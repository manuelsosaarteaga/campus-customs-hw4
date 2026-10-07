"""Campus Customs shopping agent: PydanticAI over OpenAI via the Portkey gateway."""

import logging
import os
import re
import time
import uuid
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext, capture_run_messages
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from audit import append_audit_entry, build_entry
from models import AgentReply, ChatResponse, ChatTurn, PageContext, ProductCard
from tools import AGENT_TOOLS, AgentDeps, product_card, resolve_page, search_catalogue

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# hw4/.env first, then the course-root .env; real environment variables always win.
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROJECT_ROOT.parents[1] / ".env", override=False)

log = logging.getLogger("campus_customs.agent")

PORTKEY_GATEWAY_URL = "https://api.portkey.ai/v1"
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-5.6-luna")
# One request = one model call; a turn normally needs 2-3 (search, maybe details, answer).
USAGE_LIMITS = UsageLimits(request_limit=8)
# "$68" / "$68.00" in a reply; amounts right after budget words ("under $40") are the shopper's, not prices.
PRICE_RE = re.compile(r"(?<![\w$])\$(\d{1,4}(?:,\d{3})*(?:\.\d{1,2})?)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
BUDGET_WORDS = re.compile(r"(under|below|less than|up to|max(imum)?|budget( of)?|within|over|above|around|about)\s*$", re.I)
# AI client limits: a hung request gives up after 45s; transient errors (429, 5xx, timeouts, connection
# drops) are retried by the OpenAI SDK with exponential backoff before we fall back.
REQUEST_TIMEOUT_S = 45
MAX_TRANSIENT_RETRIES = 2
FALLBACK_CARDS = 8
# Set CHAT_SIMULATE_OUTAGE=1 to force the fallback path (for demos/grading).
SIMULATE_OUTAGE = os.getenv("CHAT_SIMULATE_OUTAGE") == "1"
# Shown when the provider's content filter blocks a message (e.g. jailbreak attempts).
BLOCKED_REPLY = (
    "Sorry, I can't help with that. I'm here to help you find Campus Customs gear — "
    "ask me about hoodies, sizes, prices, or stock!"
)


@lru_cache(maxsize=1)
def get_agent() -> Agent[AgentDeps, AgentReply]:
    """Build the agent once, on first use, so a missing key fails the request instead of server startup."""
    api_key = os.getenv("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw4/.env or export it in your shell.")
    client = AsyncOpenAI(
        base_url=PORTKEY_GATEWAY_URL, api_key=api_key, timeout=REQUEST_TIMEOUT_S, max_retries=MAX_TRANSIENT_RETRIES
    )
    model = OpenAIChatModel(CHAT_MODEL, provider=OpenAIProvider(openai_client=client))
    agent = Agent(
        model,
        deps_type=AgentDeps,
        output_type=AgentReply,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        tools=AGENT_TOOLS,
        retries=3,  # covers tool-arg errors and output-validator retries
    )

    @agent.instructions
    def shopper_context(ctx: RunContext[AgentDeps]) -> str:
        d = ctx.deps
        if d.user_id is None:
            return "## Current shopper\nGuest (not logged in). Their chat is not saved between visits."
        return (
            "## Current shopper\n"
            f"Logged in as {d.user_name} (first name: {d.user_first_name}, email: {d.user_email}). "
            "Earlier messages in this conversation were loaded from their saved chat history."
        )

    @agent.instructions
    def page_context(ctx: RunContext[AgentDeps]) -> str:
        page = ctx.deps.page
        lines = ["## Current page", f"The shopper is on {page.path} ({page.kind} page)."]
        if page.product:
            p = page.product
            lines.append(
                f'They are viewing the product page for "{p["name"]}" (product_id: {p["product_id"]}, {p["garment_type"]}). '
                'Words like "this", "it", "this one", or "the one I\'m looking at" refer to this product unless they clearly '
                "mean something else. Use this product_id with your tools."
            )
        elif page.kind == "product":
            lines.append("They are on a product page for an item that isn't in the catalogue.")
        if page.visible_products:
            listed = "; ".join(f'{i}. {v["name"]} ({v["product_id"]})' for i, v in enumerate(page.visible_products, 1))
            lines.append(f"Product cards from the chat currently shown on the page, in order: {listed}. "
                         '"The first one", "the second one", etc. refer to this list.')
        return "\n".join(lines)

    @agent.output_validator
    def prices_come_from_tools(ctx: RunContext[AgentDeps], reply: AgentReply) -> AgentReply:
        """Reject replies that quote a price no tool returned this turn (stops hallucinated or stale prices)."""
        unverified = []
        for m in PRICE_RE.finditer(reply.message):
            if BUDGET_WORDS.search(reply.message[: m.start()]):
                continue
            amount = round(float(m.group(1).replace(",", "")), 2)
            if amount not in ctx.deps.seen_prices:
                unverified.append(m.group(0))
        if unverified:
            raise ModelRetry(
                f"Your reply quotes {', '.join(unverified)} but no tool returned that price in this turn. "
                "Look the price up with get_price or search_products and quote price_display exactly, "
                "or remove the price."
            )
        return reply

    @agent.output_validator
    def no_other_emails(ctx: RunContext[AgentDeps], reply: AgentReply) -> AgentReply:
        """Safety: the only email a reply may contain is the logged-in shopper's own."""
        own = (ctx.deps.user_email or "").lower()
        leaked = [e for e in EMAIL_RE.findall(reply.message) if e.lower() != own]
        if leaked:
            raise ModelRetry("Never include email addresses other than the logged-in shopper's own. Remove them.")
        return reply

    return agent


def to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Replay earlier turns; assistant turns note which cards they showed so "the second one" still resolves."""
    messages: list[ModelMessage] = []
    for turn in history:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            text = turn.content
            if turn.product_ids:
                text += f"\n\n(Cards shown on the page with this reply: {', '.join(turn.product_ids)})"
            messages.append(ModelResponse(parts=[TextPart(content=text)]))
    return messages


def build_cards(product_ids: list[str], allowed: set[str]) -> list[ProductCard]:
    """Turn agent-chosen ids into cards using fresh DB data; drop ids the tools never returned."""
    cards = (product_card(pid) for pid in dict.fromkeys(product_ids) if pid in allowed)
    return [c for c in cards if c is not None]


async def run_chat(
    message: str, history: list[ChatTurn], user: dict | None = None, page: PageContext | None = None
) -> ChatResponse:
    page_info = resolve_page(page)
    deps = AgentDeps(
        user_id=user["id"] if user else None,
        user_first_name=user["first_name"] if user else None,
        user_name=user["name"] if user else None,
        user_email=user["email"] if user else None,
        page=page_info,
    )
    # Products the shopper can see are DB-verified, so the agent may show them as cards (prices still need tools).
    if page_info.product:
        deps.seen_product_ids.add(page_info.product["product_id"])
    deps.seen_product_ids.update(v["product_id"] for v in page_info.visible_products)
    run_id, started = str(uuid.uuid4()), time.time()
    history_messages = to_message_history(history)
    result, stop_reason = None, "final_result"
    with capture_run_messages() as messages:  # keeps the run's messages even if it fails, for the audit trail
        try:
            if SIMULATE_OUTAGE:
                raise RuntimeError("Simulated AI outage (CHAT_SIMULATE_OUTAGE=1)")
            result = await get_agent().run(
                message,
                deps=deps,
                message_history=history_messages,
                usage_limits=USAGE_LIMITS,
            )
        except ModelHTTPError as e:
            if "content_filter" in str(e.body):
                stop_reason = "content_filter"
            else:
                log.exception("Model error; serving database fallback")
                stop_reason = f"fallback:{type(e).__name__}"
        except Exception as e:
            # Timeouts after retries, usage limits, repeated invalid output, missing key, outages...
            log.exception("Agent failed; serving database fallback")
            stop_reason = f"fallback:{type(e).__name__}"

    if result is not None:
        reply: AgentReply = result.output
        log.info("chat tools=%s cards=%s", deps.tool_calls, reply.product_ids)
        cards = build_cards(reply.product_ids, deps.seen_product_ids)
        title = (reply.results_title or "Matching items") if cards else None
        response = ChatResponse(reply=reply.message, products=cards, results_title=title)
    elif stop_reason == "content_filter":
        response = ChatResponse(reply=BLOCKED_REPLY)
    else:
        response = fallback_response(message, page_info)

    append_audit_entry(build_entry(
        run_id=run_id, model=CHAT_MODEL, started=started, finished=time.time(),
        messages=list(messages), history_len=len(history_messages),
        user_id=deps.user_id, page=page_info.path, message=message, stop_reason=stop_reason,
        reply=response.reply, product_ids=[c.product_id for c in response.products], degraded=response.degraded,
        usage=result.usage if result is not None else None,
    ))
    return response


def fallback_response(message: str, page_info) -> ChatResponse:
    """When the AI is unavailable, still help: plain DB search on the shopper's words (no AI involved)."""
    found = search_catalogue(message, limit=FALLBACK_CARDS)
    ids = [r.product_id for r in found.results]
    if not ids and page_info.product:
        ids = [page_info.product["product_id"]]
    cards = [c for c in (product_card(pid) for pid in ids) if c]
    if cards:
        fixed = f" (showing results for {', '.join(found.corrections.values())})" if found.corrections else ""
        reply = (
            "Sorry, our assistant is having trouble right now. Meanwhile, here are items from our catalogue "
            f"that match your question{fixed}. Tap “Try again” in a moment for a full answer."
        )
        return ChatResponse(reply=reply, products=cards, results_title="Catalogue matches", degraded=True)
    return ChatResponse(
        reply="Sorry, our assistant is having trouble right now. Please tap “Try again” in a moment, "
              "or browse the Products page.",
        degraded=True,
    )
