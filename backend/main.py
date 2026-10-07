"""Campus Customs API: catalogue, images, auth, and the chat agent.

Run from backend/:  uvicorn main:app --port 8000   (or: python main.py)
"""

import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import CHAT_MODEL, run_chat
from audit import append_audit_entry, now_iso, redact
from auth import make_router
from models import AuditEntry, ChatHistory, ChatRequest, ChatResponse
from tools import (
    DATA_DIR, clear_chat_history, fetch_product, get_db, load_history_turns, load_saved_messages, product_from_row,
    rank_catalogue, save_chat_turn, stock_summaries,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     %(name)s - %(message)s")
log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Strip submitted values so passwords are never echoed back in error responses.
    errors = [{"loc": e["loc"], "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


# image_file_path in the DB looks like "products/x.jpg", so it resolves under /static/.
app.mount("/static/products", StaticFiles(directory=DATA_DIR / "products"), name="products")

auth_router, current_user, optional_user = make_router(get_db)
app.include_router(auth_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "chat_model": CHAT_MODEL}


EMPTY_STOCK = {"available_sizes": [], "low_stock_sizes": [], "in_stock": False}


@app.get("/api/products")
def list_products() -> list[dict]:
    """Every product plus a stock summary (powers the "Sold out" / "Only N sizes left" badges)."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    stock = stock_summaries()
    return [{**product_from_row(r), **stock.get(r["product_id"], EMPTY_STOCK)} for r in rows]


@app.get("/api/search")
def search(q: str = Query(min_length=1, max_length=200)) -> dict:
    """Typo-tolerant catalogue search for the Products page (same ranking the agent's search tool uses)."""
    scored, corrections = rank_catalogue(q)
    stock = stock_summaries()
    products = [{**p, **stock.get(p["product_id"], EMPTY_STOCK)} for _, p in scored]
    return {"query": q, "corrections": corrections, "products": products}


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    product = fetch_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


# Safety: simple per-client rate limit on the (paid) AI endpoint.
CHAT_RATE_LIMIT = 20  # messages
CHAT_RATE_WINDOW_S = 60  # per rolling minute
_chat_hits: dict[str, deque] = defaultdict(deque)


def check_rate_limit(key: str) -> bool:
    now, hits = time.monotonic(), _chat_hits[key]
    while hits and now - hits[0] > CHAT_RATE_WINDOW_S:
        hits.popleft()
    if len(hits) >= CHAT_RATE_LIMIT:
        return False
    hits.append(now)
    return True


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request, user: dict | None = Depends(optional_user)) -> ChatResponse:
    client = f"user:{user['id']}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    if not check_rate_limit(client):
        append_audit_entry(AuditEntry(
            timestamp=now_iso(), run_id=str(uuid.uuid4()), model=CHAT_MODEL, user_id=user["id"] if user else None,
            page=body.page.path if body.page else None, message=redact(body.message[:300]), stop_reason="rate_limited",
            reply="(rejected: rate limit)",
        ))
        raise HTTPException(status_code=429, detail="You're sending messages very quickly. Please wait a moment and try again.")
    # Logged-in shoppers: the saved DB history is the source of truth (client-sent history is ignored).
    # Guests: use the in-browser history the widget sends; nothing is stored.
    history = load_history_turns(user["id"]) if user else body.history
    try:
        response = await run_chat(body.message, history, user, body.page)
    except Exception:
        log.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail="The assistant is having trouble right now. Please try again.")
    # Fallback (degraded) answers aren't saved, so "Try again" doesn't leave duplicates in history.
    if user and not response.degraded:
        save_chat_turn(user["id"], body.message, response.reply, response.products)
    return response


@app.get("/api/chat/history")
def chat_history(user: dict = Depends(current_user)) -> ChatHistory:
    return ChatHistory(messages=load_saved_messages(user["id"]))


@app.delete("/api/chat/history")
def delete_chat_history(user: dict = Depends(current_user)) -> dict:
    return {"deleted": clear_chat_history(user["id"])}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
