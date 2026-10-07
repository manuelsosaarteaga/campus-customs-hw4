"""Pydantic types shared by the chat API, the agent, and its tools."""

from typing import Literal

from pydantic import BaseModel, Field

MAX_CARDS = 12

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
StockStatus = Literal["in_stock", "low_stock", "sold_out"]


# ---- Tool results (what the agent sees from the database) --------------------------------------


class ProductSuggestion(BaseModel):
    """A close match offered when a lookup can't find the exact product."""

    product_id: str
    name: str


class ProductNotFound(BaseModel):
    """Returned instead of guessing when a product_id/name doesn't match the catalogue."""

    found: Literal[False] = False
    query: str = Field(description="The product_id or name the agent asked for.")
    message: str
    suggestions: list[ProductSuggestion] = Field(default_factory=list)


class ProductSummary(BaseModel):
    """One search hit: enough to recommend an item and answer "is it in stock?" at a glance."""

    product_id: str
    name: str
    garment_type: str
    price: float
    price_display: str = Field(description='Exact price string to quote, e.g. "$68.00".')
    colors: list[str]
    in_stock_sizes: list[Size]
    low_stock_sizes: list[Size]
    sold_out_sizes: list[Size]


class SearchResults(BaseModel):
    query: str
    total_matches: int = Field(description="Matches before the limit was applied.")
    corrections: dict[str, str] = Field(
        default_factory=dict,
        description='Misspelled words that were auto-corrected, e.g. {"crewnek": "crewneck"}. Mention the correction to the shopper.',
    )
    results: list[ProductSummary]


class ProductDescription(BaseModel):
    """Answers "what does it look like / what is it made of?" Deliberately excludes price and stock."""

    found: Literal[True] = True
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    tags: list[str]


class PriceInfo(BaseModel):
    """Answers "how much is it?" with a single authoritative number from the catalogue."""

    found: Literal[True] = True
    product_id: str
    name: str
    price: float
    currency: Literal["USD"] = "USD"
    price_display: str = Field(description='Exact price string to quote, e.g. "$68.00".')


class SizeStock(BaseModel):
    size: Size
    quantity: int = Field(ge=0)
    status: StockStatus


class StockReport(BaseModel):
    """Answers "do you have it in M?" — per-size quantities plus a ready-made status for each."""

    found: Literal[True] = True
    product_id: str
    name: str
    requested_size: Size | None = Field(description="Size the shopper asked about, if any.")
    requested_size_status: StockStatus | None = Field(description="Status of requested_size; null if no size asked.")
    sizes: list[SizeStock] = Field(description="Every size, XS→XXL (or only the requested size).")
    available_sizes: list[Size]
    sold_out_sizes: list[Size]
    total_quantity: int


class ShopperProfile(BaseModel):
    """Who the agent is talking to. Only ever the logged-in shopper's own account; never password data."""

    logged_in: bool
    first_name: str | None = None
    name: str | None = None
    email: str | None = None
    member_since: str | None = Field(default=None, description="Account creation date (YYYY-MM-DD).")
    saved_messages: int = Field(default=0, description="How many chat messages are saved for this shopper.")


class InvalidSize(BaseModel):
    """Returned when the shopper asks for a size the store doesn't carry (e.g. XXXL, 10)."""

    found: Literal[False] = False
    product_id: str
    requested: str
    message: str
    valid_sizes: list[Size]


# ---- Agent output and chat API ------------------------------------------------------------------


class AgentReply(BaseModel):
    """Structured output the agent must return for every chat turn."""

    message: str = Field(description="The reply shown to the shopper in the chat window. Short, friendly, plain text.")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_CARDS,
        description="product_id values (from tool results only) to show as product cards on the page, most relevant first.",
    )
    results_title: str | None = Field(
        default=None,
        max_length=60,
        description='Short heading for the cards shown on the page, e.g. "Hoodies" or "Navy crewnecks under $60". Null if no cards.',
    )


class ProductCard(BaseModel):
    """A product the frontend renders as a card on the page. Built from the DB, never from model text."""

    product_id: str = Field(description="Links the card to /products/{product_id} (single-item view).")
    name: str
    garment_type: str
    price: float
    price_display: str
    image_url: str
    short_description: str
    colors: list[str]
    in_stock: bool
    available_sizes: list[Size]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)
    product_ids: list[str] = Field(default_factory=list, max_length=MAX_CARDS, description="Cards shown with this turn.")


class PageContext(BaseModel):
    """What the shopper is looking at when they send a message (sent by the frontend, verified by the backend)."""

    path: str = Field(default="/", max_length=300, description='Current route, e.g. "/products/basic-hoodie-big-yale".')
    product_id: str | None = Field(default=None, max_length=120, description="Product on screen, if on an item page.")
    visible_product_ids: list[str] = Field(
        default_factory=list, max_length=MAX_CARDS, description="Chat result cards currently shown on the page, in order."
    )


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Guests only: logged-in shoppers' history is loaded from the database instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None


class SavedMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    messages: list[SavedMessage]


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    results_title: str | None = Field(default=None, description="Heading for the on-page results; null when products is empty.")
    degraded: bool = Field(default=False, description="True when the AI failed and this is a database-only fallback answer.")


# ---- Audit trail (output/audit_trail.json) --------------------------------------------------------


class AuditToolCall(BaseModel):
    """One tool call the agent made during a chat turn."""

    tool: str
    args: dict = Field(default_factory=dict, description="Arguments the model passed (as sent).")
    result: str = Field(description="Short summary of what the tool returned (truncated).")
    ok: bool = Field(description="False if the tool returned an error/not-found or raised a retry.")
    timestamp: str | None = None


class AuditEntry(BaseModel):
    """One chat turn: who asked, what the agent did, and why it stopped."""

    timestamp: str
    run_id: str
    model: str
    user_id: int | None = Field(description="Logged-in user id (no email or name, to keep PII out of logs).")
    page: str | None = Field(description="Page path the shopper was on.")
    message: str = Field(description="Shopper message (truncated).")
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    retries: list[str] = Field(default_factory=list, description="Retry prompts sent back to the model (validator/tool errors).")
    model_requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = Field(description='"final_result" | "content_filter" | "fallback:<ErrorType>" | "rate_limited"')
    reply: str = Field(description="Reply shown to the shopper (truncated).")
    product_ids: list[str] = Field(default_factory=list)
    degraded: bool = False
    duration_ms: int = 0
