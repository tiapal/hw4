"""Pydantic types for the Campus Customs API and chat agent."""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field, field_validator

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


# --- Products -----------------------------------------------------------------

class ProductCard(BaseModel):
    """A product as the website shows it (list, detail page, and chat cards)."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    price: float
    image_url: str
    in_stock: bool | None = None  # only filled in for the product list


class ProductSummary(BaseModel):
    """One search hit from find_products. It only identifies the product (no price or stock)."""

    product_id: str = Field(description="Pass this to get_product_info or get_stock")
    name: str
    garment_type: str
    colors: list[str]
    matches_all_words: bool = Field(
        default=True,
        description="False if this product matches only some of the words searched for (a loose, partial match)",
    )


class ProductInfo(BaseModel):
    """Result of get_product_info: the facts that come straight from the catalogue table."""

    product_id: str
    name: str
    description: str
    price: float = Field(description="Price in US dollars")
    colors: list[str]


class PageSearchResult(BaseModel):
    """Result of show_products_on_page, as the agent sees it. The full cards go to the website, not to the model."""

    query: str
    total_found: int = Field(description="How many catalogue products match every word of the query")
    shown_on_page: bool = Field(description="True if these products are now showing on the shop page")
    items: list[ProductSummary] = Field(description="Up to 10 of the matches, so you can describe them")


class FitInfo(BaseModel):
    """Result of get_item_fit: how an item is cut, or 'unknown' when the shop has no information."""

    product_id: str
    name: str
    fit: Literal["fitted", "regular", "oversized", "unknown"]
    source: str | None = Field(default=None, description="Where the fit came from: the fit column, the description, tags, or name")
    evidence: str | None = Field(default=None, description="The exact words found, e.g. 'oversized fit'")


class ChartRow(BaseModel):
    """One line of the No Boundaries x Walmart size chart (backend/size_chart.json). All measurements are inches."""

    old_size: str
    new_size: str
    campus_customs_size: Literal["XS", "S", "M", "L", "XL", "XXL"] | None = Field(
        description="The matching size Campus Customs makes. None means we don't make that size."
    )
    numeric: str
    line: Literal["straight", "plus"]
    chest: float
    waist: float
    hip: float


class SizeChartResult(BaseModel):
    """Result of lookup_size_chart: what the chart says for a chest measurement or a usual size."""

    basis: str = Field(description="Where these numbers come from. Always tell the shopper this.")
    asked: str = Field(description="What was looked up, e.g. 'chest 34 in'")
    covered: bool = Field(description="False if the chart doesn't cover it. Then there are no sizes to give.")
    exact: bool = Field(description="True if the chart lists exactly this value")
    matches: list[ChartRow] = Field(
        default_factory=list, description="The chart rows that apply, or the rows just below and above when not listed"
    )
    chart_size: str | None = Field(default=None, description="The chart's size label for the closest row")
    campus_customs_size: str | None = Field(default=None, description="The Campus Customs size that matches, if we make it")
    notes: list[str] = Field(default_factory=list)


class SizeRecommendation(BaseModel):
    """Result of recommend_size: a size for one item, from the chart, the shopper's fit choice, and real stock."""

    product_id: str
    name: str
    fit_choice: Literal["fitted", "perfect", "oversized"]
    chart: SizeChartResult
    recommended_size: str | None = Field(
        default=None, description="The Campus Customs size after applying the fit choice. None if the chart can't say."
    )
    recommended_chart_size: str | None = Field(default=None, description="The chart's label for that size")
    in_stock: bool | None = Field(default=None, description="Whether recommended_size is in stock. None if no size.")
    quantity: int | None = Field(default=None, description="Units of recommended_size on hand")
    closest_in_stock: str | None = Field(
        default=None, description="Set when recommended_size is sold out or not made: the nearest size that IS in stock"
    )
    closest_in_stock_quantity: int | None = None
    item_fit: FitInfo
    item_fit_note: str = Field(description="What this item's own cut means for the recommendation")
    notes: list[str] = Field(default_factory=list)


class LookupBlocked(BaseModel):
    """Returned instead of a lookup result once two database checks for something have come back empty."""

    blocked: Literal[True] = True
    message: str = Field(description="Tells the agent to stop searching and say the item can't be found")


class SizeStock(BaseModel):
    size: Literal["XS", "S", "M", "L", "XL", "XXL"]
    quantity: int = Field(description="Units on hand. 0 means sold out in this size.")
    in_stock: bool


class StockResult(BaseModel):
    """Result of get_stock: units on hand from the inventory table."""

    product_id: str
    name: str
    requested_size: str | None = Field(
        default=None, description="The size the customer asked about, cleaned up (e.g. 'medium' -> 'M'). None if no size was asked."
    )
    size_carried: bool | None = Field(
        default=None,
        description="False if the customer asked for a size we don't make (we only sell XS, S, M, L, XL, XXL). None if no size was asked.",
    )
    sizes: list[SizeStock] = Field(
        description="Just the requested size, or every size (XS to XXL) when no size was asked or the size isn't carried."
    )


# --- Chat ---------------------------------------------------------------------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=2000)


class PageContext(BaseModel):
    """Where the shopper is on the site. Sent by the website; the server re-checks it against the database."""

    path: str = Field(max_length=200, description="The page's URL path, e.g. /products/basic-hoodie-big-yale")
    product_id: str | None = Field(default=None, max_length=100, description="Set when a product page is open")


class ShopperInfo(BaseModel):
    """Who is chatting. Built on the server from the login session, never from anything the website sends."""

    is_guest: bool = True
    user_id: int | None = None  # used only to label the audit trail; never shown to the model
    name: str | None = None
    first_name: str | None = None
    email: str | None = None


class SavedMessage(BaseModel):
    """One stored chat message (a row of the chat_messages table), as the website and the agent see it."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatHistory(BaseModel):
    """What GET /api/chat/history returns."""

    messages: list[SavedMessage]


class ChatRequest(BaseModel):
    """What the website sends to POST /api/chat."""

    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests (nothing is stored for them). For logged-in shoppers the server loads history itself.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message can't be blank")
        return v


class AgentReply(BaseModel):
    """The agent's structured answer."""

    message: str = Field(description="The reply to show the shopper, in plain text")
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id values (from find_products results only) to show as product cards, at most 3",
    )


class SearchResults(BaseModel):
    """Catalogue matches for the website to show as product cards on the Products page."""

    query: str
    total: int = Field(description="How many products matched (can be more than the cards sent)")
    products: list[ProductCard]


class ChatReply(BaseModel):
    """What POST /api/chat returns: the reply, plus (when the shopper asked about a type of item)
    the search results to show on the page. All cards are built from the database."""

    message: str
    products: list[ProductCard] = Field(default_factory=list)  # a few cards to show inside the chat
    search: SearchResults | None = None  # matches to show on the Products page


@dataclass
class ChatDeps:
    """Per-request context handed to the agent and its tools."""

    shopper: ShopperInfo = field(default_factory=ShopperInfo)
    page_label: str | None = None  # e.g. "the About Us page", worked out on the server from the path
    page_product: ProductInfo | None = None  # the product page that is open, looked up in the database
    seen_ids: set[str] = field(default_factory=set)  # products the lookup tool has returned this turn
    misses: int = 0  # database lookups this turn that found nothing (after 2, lookups are blocked)
    lookup_limit_hit: bool = False  # True if a lookup was blocked because of that limit
    sensitive_removed: list[str] = field(default_factory=list)  # kinds of private details taken out of the shopper's message
    page_search: SearchResults | None = None  # set by show_products_on_page; sent to the website
