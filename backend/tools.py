"""Tools the Campus Customs agent can call, plus the product-database helpers they share with the API.

Tables used (data/campus_customs.db):
    catalogue(product_id, name, garment_type, description, colors, search_tags, image_file_path, price)
    inventory(id, product_id, size, quantity)          one row per product and size

To add a tool: write an async function with a RunContext first argument and a docstring
(the docstring is what the model reads), then add it to TOOLS at the bottom.
"""

import json
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_ai import ModelRetry, RunContext

from models import (
    SIZE_ORDER,
    ChartRow,
    ChatDeps,
    FitInfo,
    LookupBlocked,
    PageSearchResult,
    ProductCard,
    ProductInfo,
    ProductSummary,
    SearchResults,
    SizeChartResult,
    SizeRecommendation,
    SizeStock,
    StockResult,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
# data/products_white/ has the same photos with black backgrounds made white (scripts/whiten_product_photos.py).
# The originals in data/products/ are never changed. Use the white set when it exists.
IMAGE_DIR = DATA_DIR / "products_white" if (DATA_DIR / "products_white").is_dir() else DATA_DIR / "products"

STOPWORDS = {
    "a", "an", "the", "do", "does", "you", "your", "have", "any", "in", "for", "with", "on", "of", "to",
    "me", "i", "is", "are", "what", "show", "got", "looking", "want", "need", "something", "anything",
    "and", "or", "please", "this", "that", "it", "u", "can", "how", "much", "does", "come", "carry",
}
# Shoppers and the catalogue don't always use the same word.
SYNONYMS = {
    "hoodie": ["hooded"],
    "tee": ["t-shirt"],
    "shirt": ["t-shirt"],
    "sweater": ["sweatshirt", "crewneck"],
    "jacket": ["fleece", "bomber"],
    "zip": ["quarter-zip", "full-zip"],
}


# --- Database helpers (also used by main.py) ------------------------------------

def connect_readonly() -> sqlite3.Connection:
    """Open the shop database read-only so the product API and the agent can never change it."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def image_url(file_name: str) -> str:
    """URL of a product photo. The ?v= number is the file's modified time, so browsers re-download a changed photo."""
    path = IMAGE_DIR / file_name
    return f"/api/images/{file_name}?v={int(path.stat().st_mtime) if path.exists() else 0}"


def row_to_card(row: sqlite3.Row, in_stock: bool | None = None) -> ProductCard:
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        price=row["price"],
        image_url=image_url(Path(row["image_file_path"]).name),
        in_stock=in_stock,
    )


def cards_for(product_ids: list[str]) -> list[ProductCard]:
    """Product cards for these ids, in the given order. Built from the database, never from model text."""
    if not product_ids:
        return []
    marks = ",".join("?" * len(product_ids))
    with connect_readonly() as conn:
        rows = {r["product_id"]: r for r in conn.execute(
            f"SELECT * FROM catalogue WHERE product_id IN ({marks})", product_ids)}
    return [row_to_card(rows[i]) for i in product_ids if i in rows]


def _search_terms(query: str) -> list[str]:
    terms = []
    for word in re.findall(r"[a-z0-9'-]+", query.lower()):
        if word in STOPWORDS:
            continue
        if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
            word = word[:-1]  # hoodies -> hoodie, shirts -> shirt
        terms.append(word)
    return terms


# --- Lookups (plain functions, so they can be tested without the model) ----------

# What shoppers type -> the size codes stored in inventory.size
SIZE_ALIASES = {
    "xs": "XS", "extrasmall": "XS",
    "s": "S", "small": "S",
    "m": "M", "med": "M", "medium": "M",
    "l": "L", "large": "L",
    "xl": "XL", "xlarge": "XL", "extralarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xxlarge": "XXL", "extraextralarge": "XXL",
}


def normalize_size(raw: str) -> str:
    key = re.sub(r"[^a-z0-9]", "", raw.lower())
    return SIZE_ALIASES.get(key, raw.strip().upper())


PAGE_RESULT_LIMIT = 36  # most cards the Products page will show for one chat search


def _term_matches(term: str, haystack: str) -> bool:
    return any(re.search(r"\b" + re.escape(w), haystack) for w in [term, *SYNONYMS.get(term, [])])


def search_for_page(query: str, limit: int = PAGE_RESULT_LIMIT) -> tuple[list[ProductCard], int]:
    """Products that match EVERY word of the query (in name, type, colors, or tags). Returns (cards, total matches).

    Stricter than search_catalogue on purpose: this fills the page, so "pink hoodie" must not
    return every hoodie. The description is left out so a tee that merely mentions a hoodie isn't a hoodie hit.
    """
    terms = _search_terms(query)
    if not terms:
        return [], 0
    with connect_readonly() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id ORDER BY c.name
            """
        ).fetchall()
    hits = []
    for row in rows:
        haystack = " ".join([row["name"], row["garment_type"], row["colors"], row["search_tags"]]).lower()
        if all(_term_matches(t, haystack) for t in terms):
            hits.append(row)
    return [row_to_card(r, in_stock=r["total_stock"] > 0) for r in hits[:limit]], len(hits)


def search_catalogue(query: str, limit: int = 5) -> list[ProductSummary]:
    """Rank products by how many of the query's words appear in their name, type, description, colors, or tags."""
    terms = _search_terms(query)
    with connect_readonly() as conn:
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
    scored = []
    for row in rows:
        haystack = " ".join(
            [row["name"], row["garment_type"], row["description"], row["colors"], row["search_tags"]]
        ).lower()
        score = sum(_term_matches(t, haystack) for t in terms)
        if score or not terms:
            scored.append((score, row))
    scored.sort(key=lambda s: (-s[0], s[1]["name"]))
    return [
        ProductSummary(
            product_id=r["product_id"], name=r["name"], garment_type=r["garment_type"], colors=json.loads(r["colors"]),
            matches_all_words=bool(terms) and score == len(terms),  # a partial match is only "closest", not "found"
        )
        for score, r in scored[:limit]
    ]


def lookup_product_info(product_id: str) -> ProductInfo | None:
    with connect_readonly() as conn:
        row = conn.execute(
            "SELECT product_id, name, description, price, colors FROM catalogue WHERE product_id = ?",
            (product_id,),
        ).fetchone()
    if row is None:
        return None
    return ProductInfo(
        product_id=row["product_id"], name=row["name"], description=row["description"],
        price=row["price"], colors=json.loads(row["colors"]),
    )


def lookup_stock(product_id: str, size: str | None = None) -> StockResult | None:
    with connect_readonly() as conn:
        product = conn.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if product is None:
            return None
        rows = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    all_sizes = [
        SizeStock(size=r["size"], quantity=r["quantity"], in_stock=r["quantity"] > 0)
        for r in sorted(rows, key=lambda r: SIZE_ORDER.index(r["size"]))
    ]
    if not size:
        return StockResult(product_id=product_id, name=product["name"], sizes=all_sizes)

    wanted = normalize_size(size)
    match = [s for s in all_sizes if s.size == wanted]
    if not match:  # a size we don't make: say so, and show what we do have
        return StockResult(
            product_id=product_id, name=product["name"], requested_size=wanted, size_carried=False, sizes=all_sizes
        )
    return StockResult(
        product_id=product_id, name=product["name"], requested_size=wanted, size_carried=True, sizes=match
    )



# --- Sizing: the size chart and item fit (plain functions, testable without the model) --------

CHART_FILE = Path(__file__).resolve().parent / "size_chart.json"  # the chart picture, written out as data
CC_SIZES = ["XS", "S", "M", "L", "XL", "XXL"]  # sizes Campus Customs makes, smallest to largest
FIT_STEPS = {"fitted": -1, "perfect": 0, "oversized": +1}  # fitted = one size down, oversized = one size up

# How an item's cut can be spotted in its listing text (the catalogue has no fit data, so this is only a fallback).
FIT_WORDS = {
    "oversized": r"oversized|over-sized|boxy|loose[- ]fit(?:ting)?",
    "fitted": r"fitted|slim[- ]fit|trim[- ]fit|tailored|athletic[- ]fit",
    "regular": r"regular[- ]fit|classic[- ]fit|standard[- ]fit|true to size",
}
FIT_NOTES = {
    ("oversized", "fitted"): "This item is cut oversized, so one size down may fit closer to a regular fit instead of snug.",
    ("oversized", "perfect"): "This item is already cut oversized, so your exact size will already feel loose.",
    ("oversized", "oversized"): "This item is already cut oversized, so one size up will be very roomy. Perfect sizing may be enough.",
    ("fitted", "fitted"): "This item is already cut fitted, so one size down may feel tight.",
    ("fitted", "perfect"): "This item is cut fitted, so it will sit close to the body at your exact size.",
    ("fitted", "oversized"): "This item is cut fitted, so one size up may fit closer to a regular fit instead of baggy.",
    ("regular", "fitted"): "This item has a regular fit, so the sizes here apply as they are.",
    ("regular", "perfect"): "This item has a regular fit, so the sizes here apply as they are.",
    ("regular", "oversized"): "This item has a regular fit, so the sizes here apply as they are.",
}
UNKNOWN_FIT_NOTE = "There is no fit information for this item, so I can't say whether it runs fitted, regular, or oversized."


@lru_cache
def load_chart() -> tuple[str, list[ChartRow]]:
    """The size chart from size_chart.json: (where it comes from, its rows in chart order)."""
    data = json.loads(CHART_FILE.read_text(encoding="utf-8"))
    return data["basis"], [ChartRow(**r) for r in data["rows"]]


def _inch(x: float) -> str:
    """34.5 -> '34½', like the chart prints it."""
    whole, frac = int(x), x - int(x)
    return f"{whole}{ {0.25: '¼', 0.5: '½', 0.75: '¾'}.get(frac, '') }" if frac in (0, 0.25, 0.5, 0.75) else str(x)


def _rows_at(rows: list[ChartRow], chest: float) -> list[ChartRow]:
    return sorted((r for r in rows if r.chest == chest), key=lambda r: r.line != "straight")  # regular line first


def _alt_labels(new_size: str) -> set[str]:
    return {part.upper() for part in re.split(r"[–/-]", new_size)}  # 'XXL–XXXL/1X' -> XXL, XXXL, 1X


def chart_lookup(chest_inches: float | None = None, usual_size: str | None = None, older_label: bool = False) -> SizeChartResult:
    """What the chart says for a chest measurement (preferred) or for a size label the shopper usually wears."""
    basis, rows = load_chart()
    notes: list[str] = []

    def done(asked: str, covered: bool, exact: bool, matches: list[ChartRow], chosen: ChartRow | None) -> SizeChartResult:
        if chosen and chosen.campus_customs_size is None:
            notes.append(f"The chart size {chosen.new_size} isn't one Campus Customs makes (we make XS to XXL).")
        return SizeChartResult(
            basis=basis, asked=asked, covered=covered, exact=exact, matches=matches,
            chart_size=chosen.new_size if chosen else None,
            campus_customs_size=chosen.campus_customs_size if chosen else None, notes=notes,
        )

    if chest_inches is not None:
        asked = f"chest {_inch(chest_inches)} in"
        lo, hi = min(r.chest for r in rows), max(r.chest for r in rows)
        if not lo <= chest_inches <= hi:
            notes.append(f"The chart only lists chests from {_inch(lo)} to {_inch(hi)} inches, so it can't be used for {_inch(chest_inches)} inches. This is about the chart, not about the shopper.")
            return done(asked, False, False, [], None)
        listed = _rows_at(rows, chest_inches)
        if listed:
            return done(asked, True, True, listed, listed[0])
        below = _rows_at(rows, max(r.chest for r in rows if r.chest < chest_inches))[0]
        above = _rows_at(rows, min(r.chest for r in rows if r.chest > chest_inches))[0]
        chosen = above if (above.chest - chest_inches) <= (chest_inches - below.chest) else below  # a tie goes to the larger
        if below.new_size == above.new_size:
            notes.append(f"{_inch(chest_inches)} in isn't listed exactly, but the rows on both sides are size {chosen.new_size}.")
        else:
            notes.append(
                f"{_inch(chest_inches)} in isn't listed. It falls between {below.new_size} (chest {_inch(below.chest)}) "
                f"and {above.new_size} (chest {_inch(above.chest)}). The closest row is {chosen.new_size}."
            )
        return done(asked, True, False, [below, above], chosen)

    if usual_size and usual_size.strip():
        token = usual_size.strip()
        asked = f"usual size {token}" + (" (older sizing)" if older_label else "")
        matches = [r for r in rows if r.numeric.lower() == token.lower()]  # e.g. "8" or "14W"
        letter = False
        if not matches:
            letter, norm = True, normalize_size(token)
            if older_label:
                matches = [r for r in rows if r.old_size.upper() == norm]
            else:
                matches = [r for r in rows if r.new_size.upper() == norm] or [r for r in rows if norm in _alt_labels(r.new_size)]
        if not matches:
            notes.append(f"'{token}' isn't a size on the chart.")
            return done(asked, False, False, [], None)
        if letter and not older_label:
            notes.append("Treating your usual size as a current label. Older labels ran bigger: on the chart an old M is a new S.")
        return done(asked, True, True, matches, matches[0])

    notes.append("A chest measurement (in inches) or a usual size is needed to use the chart.")
    return done("nothing given", False, False, [], None)


def lookup_fit(product_id: str) -> FitInfo | None:
    """How an item is cut. Reads the catalogue's `fit` column first, then the listing text. Never guesses."""
    with connect_readonly() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return None
    base = {"product_id": row["product_id"], "name": row["name"]}

    stored = (row["fit"] or "").strip().lower() if "fit" in row.keys() else ""
    if stored in ("fitted", "regular", "oversized"):
        return FitInfo(**base, fit=stored, source="the fit column in the catalogue table", evidence=stored)

    found: dict[str, tuple[str, str]] = {}
    for field in ("description", "search_tags", "name"):
        for fit, pattern in FIT_WORDS.items():
            match = re.search(rf"\b({pattern})\b", row[field], re.I)
            if match:
                found.setdefault(fit, (field, match.group(0)))
    if len(found) == 1:
        (fit, (field, words)), = found.items()
        return FitInfo(**base, fit=fit, source=f"the product {field}", evidence=words)
    return FitInfo(**base, fit="unknown", evidence="conflicting wording in the listing" if found else None)


def build_recommendation(
    product_id: str, fit_choice: str, chest_inches: float | None, usual_size: str | None, older_label: bool
) -> SizeRecommendation | None:
    """The chart size, moved down/up for the fit choice, checked against this item's stock and its own fit."""
    fit = lookup_fit(product_id)
    if fit is None:
        return None
    chart = chart_lookup(chest_inches, usual_size, older_label)
    _, rows = load_chart()
    ladder = list(dict.fromkeys(r.new_size for r in rows))  # chart sizes, smallest to largest
    notes = list(chart.notes)
    rec = SizeRecommendation(
        product_id=product_id, name=fit.name, fit_choice=fit_choice, chart=chart, item_fit=fit,
        item_fit_note=FIT_NOTES.get((fit.fit, fit_choice), UNKNOWN_FIT_NOTE), notes=notes,
    )
    if not chart.covered or chart.chart_size is None:
        notes.append("The chart can't give a size for this, so there is no recommendation.")
        return rec

    step = FIT_STEPS[fit_choice]
    at = ladder.index(chart.chart_size) + step
    if not 0 <= at < len(ladder):
        notes.append(f"The chart has no size {'smaller' if step < 0 else 'larger'} than {chart.chart_size}.")
        return rec
    target = ladder[at]
    rec.recommended_chart_size = target
    rec.recommended_size = next(r.campus_customs_size for r in rows if r.new_size == target)
    word = {"fitted": "one size down", "perfect": "the exact size", "oversized": "one size up"}[fit_choice]
    notes.append(f"{fit_choice.capitalize()} is {word}: the chart's {chart.chart_size} becomes {target}.")

    stock_result = lookup_stock(product_id)
    stock = {s.size: s.quantity for s in stock_result.sizes} if stock_result else {}
    wanted = rec.recommended_size
    if wanted:
        rec.quantity = stock.get(wanted, 0)
        rec.in_stock = rec.quantity > 0
        if not rec.in_stock:
            notes.append(f"{wanted} is sold out for this item (0 in stock).")
    else:
        notes.append(f"The chart size {target} isn't one Campus Customs makes (we make XS to XXL).")

    if not wanted or not rec.in_stock:
        # Where the wanted size would sit on our XS-XXL ladder (a size we don't make sits at the nearer end).
        carried = [i for i, g in enumerate(ladder) if any(r.new_size == g and r.campus_customs_size for r in rows)]
        pos = CC_SIZES.index(wanted) if wanted else (0 if at < min(carried) else len(CC_SIZES) - 1)
        in_stock = [s for s in CC_SIZES if stock.get(s, 0) > 0]
        if in_stock:
            # Nearest size that is in stock. On a tie: fitted prefers the smaller, everything else the larger.
            best = min(in_stock, key=lambda s: (abs(CC_SIZES.index(s) - pos), CC_SIZES.index(s) if fit_choice == "fitted" else -CC_SIZES.index(s)))
            rec.closest_in_stock, rec.closest_in_stock_quantity = best, stock[best]
            notes.append(f"Closest size that is in stock: {best} ({stock[best]} in stock).")
        else:
            notes.append("No size of this item is in stock right now.")
    return rec


# --- Agent tools ---------------------------------------------------------------------

LOOKUP_LIMIT = 2  # database lookups that find nothing, allowed in one chat message. After that: "it can't be found".


def _blocked(ctx: RunContext[ChatDeps]) -> LookupBlocked | None:
    """Once two lookups this turn have found nothing, refuse to check the database again."""
    if ctx.deps.misses < LOOKUP_LIMIT:
        return None
    ctx.deps.lookup_limit_hit = True
    return LookupBlocked(
        message=(
            f"The database has already been checked {LOOKUP_LIMIT} times for this and nothing was found. "
            "Do not search again. Tell the shopper plainly that it can't be found."
        )
    )


def _unknown_product(ctx: RunContext[ChatDeps], product_id: str) -> LookupBlocked:
    """A product_id that isn't in the database counts as a failed lookup. Ask for a retry unless the limit is reached."""
    ctx.deps.misses += 1
    blocked = _blocked(ctx)
    if blocked:
        return blocked
    raise ModelRetry(f"No product with product_id '{product_id}'. Use find_products to get a valid product_id.")


async def find_products(ctx: RunContext[ChatDeps], query: str, max_results: int = 5) -> list[ProductSummary] | LookupBlocked:
    """Search the catalogue by keywords (garment type, color, team or sport, college, design) to find a product's product_id.

    Returns the best matches with name, garment type, and colors. It does NOT include price or stock:
    call get_product_info and get_stock for those. Check matches_all_words: a match with it false only matches
    some of the words (it is just the closest), so it is NOT the item. If no result matches all the words
    (or the list is empty), that counts as one of only two database checks you get for something that can't
    be found.
    """
    if blocked := _blocked(ctx):
        return blocked
    matches = search_catalogue(query, limit=max(1, min(max_results, 8)))
    if not any(m.matches_all_words for m in matches):  # nothing matched every word: that is a failed check
        ctx.deps.misses += 1
    ctx.deps.seen_ids.update(m.product_id for m in matches)
    return matches


async def get_product_info(ctx: RunContext[ChatDeps], product_id: str) -> ProductInfo | LookupBlocked:
    """Get a product's description, price, and colors from the database. Use the product_id from find_products."""
    if blocked := _blocked(ctx):
        return blocked
    info = lookup_product_info(product_id)
    if info is None:
        return _unknown_product(ctx, product_id)
    ctx.deps.seen_ids.add(info.product_id)
    return info


async def get_stock(ctx: RunContext[ChatDeps], product_id: str, size: str | None = None) -> StockResult | LookupBlocked:
    """Get how many units are in stock from the database, using the product_id from find_products.

    Pass `size` (XS, S, M, L, XL, XXL, or words like "medium") when the customer asks about one size.
    Leave `size` empty to get every size.
    """
    if blocked := _blocked(ctx):
        return blocked
    stock = lookup_stock(product_id, size)
    if stock is None:
        return _unknown_product(ctx, product_id)
    ctx.deps.seen_ids.add(stock.product_id)
    return stock


async def show_products_on_page(ctx: RunContext[ChatDeps], query: str) -> PageSearchResult | LookupBlocked:
    """Show every product matching the query as cards on the shop's Products page (the website updates live).

    Use this when the shopper asks about a TYPE of item: "what hoodies do you have", "show me tees",
    "any red quarter-zips". Every word in the query must match, so use short keywords such as
    "hoodie", "red tee", or "quarter-zip". If total_found is 0, nothing is shown and the page is unchanged,
    and it counts as one of only two database checks you get for something that can't be found: you may
    try once more with fewer or broader words. The page cards already show image, name, price, and a short
    description, so don't read them all out in your reply.
    """
    if blocked := _blocked(ctx):
        return blocked
    cards, total = search_for_page(query)
    if cards:
        ctx.deps.page_search = SearchResults(query=query.strip(), total=total, products=cards)
        ctx.deps.seen_ids.update(c.product_id for c in cards)
    else:
        ctx.deps.misses += 1
    items = [
        ProductSummary(product_id=c.product_id, name=c.name, garment_type=c.garment_type, colors=c.colors)
        for c in cards[:10]
    ]
    return PageSearchResult(query=query.strip(), total_found=total, shown_on_page=bool(cards), items=items)


async def get_item_fit(ctx: RunContext[ChatDeps], product_id: str) -> FitInfo | LookupBlocked:
    """Look up whether an item is cut fitted, regular, or oversized, using the product_id from find_products.

    Returns fit "unknown" when the shop has no fit information for the item. Never guess in that case:
    tell the shopper you don't know and ask them.
    """
    if blocked := _blocked(ctx):
        return blocked
    fit = lookup_fit(product_id)
    if fit is None:
        return _unknown_product(ctx, product_id)
    ctx.deps.seen_ids.add(fit.product_id)
    return fit


async def lookup_size_chart(
    ctx: RunContext[ChatDeps], chest_inches: float | None = None, usual_size: str | None = None, older_label: bool = False
) -> SizeChartResult:
    """Read the No Boundaries x Walmart "What's my new size?" chart for a chest measurement or a usual size.

    Give `chest_inches` ("what size is a 34 inch chest") or `usual_size` ("I'm usually a medium"; a letter like
    M or a number like 8). Set older_label=True only if the shopper says their usual size is from older or
    vintage sizing. Returns the matching chart rows (chest, waist, hip in inches) and the Campus Customs size.
    If covered is false, the chart doesn't cover it: say so. Talk only about the clothes, never the shopper's body.
    """
    return chart_lookup(chest_inches, usual_size, older_label)


async def recommend_size(
    ctx: RunContext[ChatDeps],
    product_id: str,
    fit_choice: Literal["fitted", "perfect", "oversized"],
    chest_inches: float | None = None,
    usual_size: str | None = None,
    older_label: bool = False,
) -> SizeRecommendation | LookupBlocked:
    """Recommend a size for one item. Use it once you know the item, the shopper's chest or usual size, and their fit choice.

    fit_choice: "fitted" = one size down on the chart, "perfect" = the exact chart size, "oversized" = one size up.
    Gives chest_inches OR usual_size. The result already checks this item's stock (and suggests the closest
    size in stock when the size is sold out) and says what the item's own cut means for the choice.
    """
    if blocked := _blocked(ctx):
        return blocked
    rec = build_recommendation(product_id, fit_choice, chest_inches, usual_size, older_label)
    if rec is None:
        return _unknown_product(ctx, product_id)
    ctx.deps.seen_ids.add(rec.product_id)
    return rec


TOOLS = [find_products, get_product_info, get_stock, show_products_on_page, get_item_fit, lookup_size_chart, recommend_size]
