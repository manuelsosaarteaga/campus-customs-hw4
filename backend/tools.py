"""Catalogue access and the tools the shopping agent can call. All reads go to data/campus_customs.db."""

import difflib
import json
import math
import re
import sqlite3
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    ChatTurn, InvalidSize, PageContext, PriceInfo, ProductCard, ProductDescription, ProductNotFound,
    ProductSuggestion, ProductSummary, SavedMessage, SearchResults, ShopperProfile, SizeStock, StockReport,
    StockStatus,
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 3

# Shopper wording -> canonical size.
SIZE_ALIASES = {
    "XS": "XS", "XSMALL": "XS", "EXTRASMALL": "XS",
    "S": "S", "SM": "S", "SMALL": "S",
    "M": "M", "MED": "M", "MEDIUM": "M",
    "L": "L", "LG": "L", "LARGE": "L",
    "XL": "XL", "XLARGE": "XL", "EXTRALARGE": "XL",
    "XXL": "XXL", "2XL": "XXL", "XXLARGE": "XXL", "2XLARGE": "XXL", "EXTRAEXTRALARGE": "XXL",
}

STOPWORDS = {
    "a", "an", "and", "any", "are", "do", "for", "have", "i", "in", "is", "it", "me", "my", "of", "on",
    "or", "show", "some", "something", "the", "to", "want", "with", "you", "your", "yale", "looking",
    "need", "get", "find", "got", "please", "like", "what", "which", "there",
}
# Shopper words -> words that actually appear in the catalogue.
SYNONYMS = {
    "hoodie": ["hoodie", "hooded", "hood"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie", "hooded"],
    "crew": ["crewneck"],
    "tee": ["t-shirt", "tee"],
    "tshirt": ["t-shirt"],
    "shirt": ["shirt", "t-shirt"],
    "quarter": ["quarter-zip", "1/4 zip", "1-4-zip"],
    "zip": ["zip"],
    "jacket": ["jacket", "fleece", "bomber"],
    "blue": ["blue", "navy"],
    "grey": ["gray", "grey"],
    "gray": ["gray", "grey"],
}


@dataclass
class PageInfo:
    """Page context after the backend has verified it against the database."""

    kind: str = "other"  # home | catalogue | product | about | login | signup | other
    path: str = "/"
    product: dict | None = None  # {"product_id", "name", "garment_type"} when on an item page
    visible_products: list[dict] = field(default_factory=list)  # chat cards on screen, in order


@dataclass
class AgentDeps:
    """Per-request context handed to every tool call."""

    user_id: int | None = None
    user_first_name: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    page: PageInfo = field(default_factory=PageInfo)
    # product_ids returned by tools this turn; only these may be shown as cards.
    seen_product_ids: set[str] = field(default_factory=set)
    # Prices returned by tools this turn; the reply may only quote these.
    seen_prices: set[float] = field(default_factory=set)
    tool_calls: list[str] = field(default_factory=list)

    def saw(self, product_id: str, price: float | None = None) -> None:
        self.seen_product_ids.add(product_id)
        if price is not None:
            self.seen_prices.add(round(price, 2))


# ---- Database helpers (also used by main.py routes) --------------------------------------------


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def product_from_row(row: sqlite3.Row) -> dict:
    description = row["description"]
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": description,
        "short_description": description.split(". ")[0].rstrip(".") + ".",
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": f"/static/{row['image_file_path']}",
        "price": row["price"],
    }


def load_inventory(conn: sqlite3.Connection, product_id: str) -> list[dict]:
    rows = conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall()
    return sorted(
        ({"size": r["size"], "quantity": r["quantity"]} for r in rows),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER),
    )


def stock_summaries() -> dict[str, dict]:
    """Per-product availability for every product in one grouped query (used by the product grid badges)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT product_id, size, quantity FROM inventory ORDER BY product_id"
        ).fetchall()
    out: dict[str, dict] = {}
    for r in rows:
        entry = out.setdefault(r["product_id"], {"available_sizes": [], "low_stock_sizes": []})
        if r["quantity"] > 0:
            entry["available_sizes"].append(r["size"])
        if 0 < r["quantity"] <= LOW_STOCK:
            entry["low_stock_sizes"].append(r["size"])
    for entry in out.values():
        entry["available_sizes"].sort(key=SIZE_ORDER.index)
        entry["low_stock_sizes"].sort(key=SIZE_ORDER.index)
        entry["in_stock"] = bool(entry["available_sizes"])
    return out


def fetch_product(product_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        product = product_from_row(row)
        product["inventory"] = load_inventory(conn, product_id)
    return product


def format_price(price: float) -> str:
    return f"${price:,.2f}"


def stock_status(quantity: int) -> StockStatus:
    return "sold_out" if quantity <= 0 else "low_stock" if quantity <= LOW_STOCK else "in_stock"


def normalize_size(size: str) -> str | None:
    return SIZE_ALIASES.get(re.sub(r"[^A-Z0-9]", "", size.upper()))


def _terms(word: str) -> list[str]:
    word = word.lower()
    singular = word[:-1] if word.endswith("s") and len(word) > 3 else word
    return SYNONYMS.get(word) or SYNONYMS.get(singular) or [singular]


FUZZY_CUTOFF = 0.8  # difflib similarity needed to auto-correct a word ("crewnek" -> "crewneck" is 0.93)


@lru_cache(maxsize=1)
def catalogue_vocabulary() -> tuple[str, frozenset[str]]:
    """All catalogue text (for "does this word appear anywhere?") and its distinct words (for typo matching)."""
    with get_db() as conn:
        rows = conn.execute("SELECT name, garment_type, description, colors, search_tags FROM catalogue").fetchall()
    corpus = " ".join(
        " ".join([r["name"], r["garment_type"], r["description"], " ".join(json.loads(r["colors"])), " ".join(json.loads(r["search_tags"]))])
        for r in rows
    ).lower()
    words = frozenset(w for w in re.findall(r"[a-z][a-z'-]{2,}", corpus))
    return corpus, words


def correct_word(word: str) -> str | None:
    """Return a catalogue word close to a misspelled one, or None if the word is fine or nothing is close."""
    corpus, vocab = catalogue_vocabulary()
    if len(word) < 3 or not word.isalpha() or any(t in corpus for t in _terms(word)):
        return None
    singular = word[:-1] if word.endswith("s") else word
    close = difflib.get_close_matches(singular, vocab, n=1, cutoff=FUZZY_CUTOFF)
    return close[0] if close else None


def rank_catalogue(
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
) -> tuple[list[tuple[float, dict]], dict[str, str]]:
    """Score every product against the query (with typo correction). Returns ranked (score, product) + corrections."""
    corrections: dict[str, str] = {}

    def fix(word: str) -> str:
        fixed = correct_word(word)
        if fixed:
            corrections[word] = fixed
        return fixed or word

    words = [fix(w) for w in re.findall(r"[a-z0-9'/-]+", query.lower()) if w not in STOPWORDS]
    if garment_type:
        garment_type = " ".join(fix(w) for w in garment_type.lower().split())
    if color:
        color = " ".join(fix(w) for w in color.lower().split())
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
    candidates = []  # (product, best field weight per query word)
    for row in rows:
        p = product_from_row(row)
        if max_price is not None and p["price"] > max_price:
            continue
        if garment_type and not any(t in p["garment_type"].lower() or t in p["name"].lower() for t in _terms(garment_type)):
            continue
        if color and not any(t in c.lower() for t in _terms(color) for c in p["colors"]):
            continue
        fields = [
            (p["name"].lower(), 3), (" ".join(p["search_tags"]).lower(), 2),
            (p["garment_type"].lower(), 2), (p["description"].lower(), 1), (" ".join(p["colors"]).lower(), 1),
        ]
        hits = [max((weight for text, weight in fields if any(t in text for t in _terms(w))), default=0) for w in words]
        candidates.append((p, hits))
    # Rare words count more: "branford" (1 product) outranks "sweatshirt" (60+) when both are in the query.
    n = max(len(candidates), 1)
    idf = [1 + math.log(n / max(1, sum(1 for _, h in candidates if h[i]))) for i in range(len(words))]
    scored = []
    for p, hits in candidates:
        score = sum(h * idf[i] for i, h in enumerate(hits))
        if words and score == 0:
            continue
        scored.append((score, p))
    scored.sort(key=lambda sp: (-sp[0], sp[1]["name"]))
    return scored, corrections


def search_catalogue(
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int = 12,
) -> SearchResults:
    scored, corrections = rank_catalogue(query, garment_type, color, max_price)
    results = []
    with get_db() as conn:
        for _, p in scored[: max(1, min(limit, 20))]:
            inv = load_inventory(conn, p["product_id"])
            results.append(ProductSummary(
                product_id=p["product_id"],
                name=p["name"],
                garment_type=p["garment_type"],
                price=p["price"],
                price_display=format_price(p["price"]),
                colors=p["colors"],
                in_stock_sizes=[s["size"] for s in inv if s["quantity"] > 0],
                low_stock_sizes=[s["size"] for s in inv if 0 < s["quantity"] <= LOW_STOCK],
                sold_out_sizes=[s["size"] for s in inv if s["quantity"] == 0],
            ))
    return SearchResults(query=query, total_matches=len(scored), corrections=corrections, results=results)


def product_card(product_id: str) -> ProductCard | None:
    """Card data for the frontend, always read fresh from the DB."""
    product = fetch_product(product_id)
    if product is None:
        return None
    available = [s["size"] for s in product["inventory"] if s["quantity"] > 0]
    return ProductCard(
        product_id=product_id,
        name=product["name"],
        garment_type=product["garment_type"],
        price=product["price"],
        price_display=format_price(product["price"]),
        image_url=product["image_url"],
        short_description=product["short_description"],
        colors=product["colors"],
        in_stock=bool(available),
        available_sizes=available,
    )


# ---- Customer memory: saved chat history (logged-in shoppers only) ---------------------------------

MODEL_HISTORY_MESSAGES = 20  # most recent saved messages replayed to the model
UI_HISTORY_MESSAGES = 50  # most recent saved messages shown in the chat widget


def _product_ids_from_json(raw: str | None) -> list[str]:
    """products_json holds a list of product objects (seed rows: full catalogue rows; ours: ProductCards)."""
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [i["product_id"] for i in items if isinstance(i, dict) and isinstance(i.get("product_id"), str)]


def _recent_messages(user_id: int, limit: int) -> list[sqlite3.Row]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_history_turns(user_id: int, limit: int = MODEL_HISTORY_MESSAGES) -> list[ChatTurn]:
    """Saved conversation as model-ready turns (oldest first)."""
    turns = []
    for r in _recent_messages(user_id, limit):
        if r["role"] in ("user", "assistant"):
            turns.append(ChatTurn(role=r["role"], content=r["content"], product_ids=_product_ids_from_json(r["products_json"])[:12]))
    return turns


def load_saved_messages(user_id: int, limit: int = UI_HISTORY_MESSAGES) -> list[SavedMessage]:
    """Saved conversation for the chat widget, with product cards rebuilt from current DB data."""
    messages = []
    for r in _recent_messages(user_id, limit):
        if r["role"] not in ("user", "assistant"):
            continue
        cards = [c for c in (product_card(pid) for pid in _product_ids_from_json(r["products_json"])[:12]) if c]
        messages.append(SavedMessage(id=r["id"], role=r["role"], content=r["content"], products=cards, created_at=r["created_at"]))
    return messages


def save_chat_turn(user_id: int, user_message: str, reply: str, cards: list[ProductCard]) -> None:
    """Store the shopper's message and the assistant's reply (with its cards) in one transaction."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, NULL)",
            (user_id, user_message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, json.dumps([c.model_dump() for c in cards])),
        )


def clear_chat_history(user_id: int) -> int:
    with get_db() as conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount


def count_saved_messages(user_id: int) -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]


# ---- Page context ----------------------------------------------------------------------------------

PAGE_KINDS = {"/": "home", "/products": "catalogue", "/about": "about", "/login": "login", "/signup": "signup"}


def resolve_page(page: PageContext | None) -> PageInfo:
    """Turn the frontend's page context into verified facts. Unknown product ids are ignored, never trusted."""
    if page is None:
        return PageInfo()
    path = page.path.split("?")[0].rstrip("/") or "/"
    info = PageInfo(kind=PAGE_KINDS.get(path, "other"), path=path)
    match = re.fullmatch(r"/products/([^/]+)", path)
    product_id = match.group(1) if match else None
    if product_id:
        info.kind = "product"
        product = fetch_product(product_id)
        if product:
            info.product = {k: product[k] for k in ("product_id", "name", "garment_type")}
    for pid in dict.fromkeys(page.visible_product_ids):
        product = fetch_product(pid)
        if product:
            info.visible_products.append({"product_id": pid, "name": product["name"]})
    return info


def resolve_product(identifier: str) -> dict | ProductNotFound:
    """Find a product by exact product_id, then by exact name; otherwise return suggestions, never a guess."""
    ident = identifier.strip()
    product = fetch_product(ident) or fetch_product(ident.lower())
    if product is None:
        with get_db() as conn:
            row = conn.execute("SELECT product_id FROM catalogue WHERE lower(name) = lower(?)", (ident,)).fetchone()
        product = fetch_product(row["product_id"]) if row else None
    if product is not None:
        return product
    hits = search_catalogue(ident.replace("-", " "), limit=3).results
    return ProductNotFound(
        query=identifier,
        message="No product matches that id or name exactly. Confirm with the shopper or use one of the suggestions.",
        suggestions=[ProductSuggestion(product_id=h.product_id, name=h.name) for h in hits],
    )


# ---- Agent tools -------------------------------------------------------------------------------


def search_products(
    ctx: RunContext[AgentDeps],
    query: str = "",
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int = 12,
) -> SearchResults:
    """Search the catalogue to find products. Use this first whenever the shopper describes what they want.

    Args:
        query: Keywords from the shopper, e.g. "Berkeley college", "lacrosse", "Harvard game", "vintage bulldog".
        garment_type: Optional filter, e.g. "hoodie", "crewneck", "t-shirt", "quarter-zip", "jacket".
        color: Optional color filter, e.g. "navy", "gray", "white".
        max_price: Optional maximum price in USD.
        limit: Max results to return (1-20, default 12). Use 12 when the shopper is browsing a category.

    Returns matching products with exact price and which sizes are in stock, low, or sold out.
    """
    ctx.deps.tool_calls.append("search_products")
    found = search_catalogue(query, garment_type, color, max_price, limit)
    for r in found.results:
        ctx.deps.saw(r.product_id, r.price)
    return found


def get_product_description(ctx: RunContext[AgentDeps], product_id: str) -> ProductDescription | ProductNotFound:
    """Look up a product's full description, colors, and style tags (no price or stock).

    Use when the shopper asks what an item looks like, what's on it, what colors it comes in, or for more detail.

    Args:
        product_id: The product_id from a search result (an exact product name also works).
    """
    ctx.deps.tool_calls.append("get_product_description")
    p = resolve_product(product_id)
    if isinstance(p, ProductNotFound):
        return p
    ctx.deps.saw(p["product_id"])
    return ProductDescription(
        product_id=p["product_id"], name=p["name"], garment_type=p["garment_type"],
        description=p["description"], colors=p["colors"], tags=p["search_tags"],
    )


def get_price(ctx: RunContext[AgentDeps], product_id: str) -> PriceInfo | ProductNotFound:
    """Look up the exact current price of one product. Use before quoting any price.

    Args:
        product_id: The product_id from a search result (an exact product name also works).
    """
    ctx.deps.tool_calls.append("get_price")
    p = resolve_product(product_id)
    if isinstance(p, ProductNotFound):
        return p
    ctx.deps.saw(p["product_id"], p["price"])
    return PriceInfo(product_id=p["product_id"], name=p["name"], price=p["price"], price_display=format_price(p["price"]))


def check_stock(
    ctx: RunContext[AgentDeps], product_id: str, size: str | None = None
) -> StockReport | ProductNotFound | InvalidSize:
    """Check live stock quantity for a product, for one size or all sizes.

    Use whenever the shopper asks about availability, a specific size, or "do you have it?".
    If a size is sold out, tell the shopper clearly and mention which sizes are available.

    Args:
        product_id: The product_id from a search result (an exact product name also works).
        size: Optional size the shopper asked about: XS, S, M, L, XL, XXL (words like "medium" are fine). Omit for all sizes.
    """
    ctx.deps.tool_calls.append("check_stock")
    p = resolve_product(product_id)
    if isinstance(p, ProductNotFound):
        return p
    ctx.deps.saw(p["product_id"])
    sizes = [SizeStock(size=s["size"], quantity=s["quantity"], status=stock_status(s["quantity"])) for s in p["inventory"]]
    requested = None
    if size:
        requested = normalize_size(size)
        if requested is None or requested not in {s.size for s in sizes}:
            return InvalidSize(
                product_id=p["product_id"], requested=size,
                message=f"'{size}' is not a size we carry for this item.", valid_sizes=[s.size for s in sizes],
            )
    match = next((s for s in sizes if s.size == requested), None)
    return StockReport(
        product_id=p["product_id"],
        name=p["name"],
        requested_size=requested,
        requested_size_status=match.status if match else None,
        sizes=[match] if match else sizes,
        available_sizes=[s.size for s in sizes if s.quantity > 0],
        sold_out_sizes=[s.size for s in sizes if s.quantity == 0],
        total_quantity=sum(s.quantity for s in sizes),
    )


def get_shopper_profile(ctx: RunContext[AgentDeps]) -> ShopperProfile:
    """Look up the logged-in shopper's own account: name, email, member-since date, saved-message count.

    Use when the shopper asks who they are logged in as, what email is on their account, or whether you remember them.
    Returns logged_in=false for guests.
    """
    ctx.deps.tool_calls.append("get_shopper_profile")
    if ctx.deps.user_id is None:
        return ShopperProfile(logged_in=False)
    with get_db() as conn:
        row = conn.execute("SELECT name, email, first_name, created_at FROM users WHERE id = ?", (ctx.deps.user_id,)).fetchone()
    if row is None:
        return ShopperProfile(logged_in=False)
    return ShopperProfile(
        logged_in=True,
        first_name=row["first_name"] or row["name"].split(" ")[0],
        name=row["name"],
        email=row["email"],
        member_since=(row["created_at"] or "")[:10] or None,
        saved_messages=count_saved_messages(ctx.deps.user_id),
    )


AGENT_TOOLS = [search_products, get_product_description, get_price, check_stock, get_shopper_profile]
