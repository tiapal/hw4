"""Campus Customs API: products, images, accounts, and the shop chatbot.

Run from inside this folder:
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import sqlite3
import time
from collections import defaultdict

from fastapi import Cookie, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from agent import MissingApiKey, run_chat
from auth import connect, init_schema, router as auth_router, user_from_session
from models import SIZE_ORDER, ChatHistory, ChatReply, ChatRequest, ChatTurn, SavedMessage, ShopperInfo
from safety import redact_sensitive
from tools import IMAGE_DIR, cards_for, connect_readonly, row_to_card

log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")
init_schema()
app.include_router(auth_router)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    # FastAPI's default 422 echoes the submitted values back, which would include passwords.
    errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


# Product photos: the white-background set when it exists (see IMAGE_DIR in tools.py), otherwise the originals.
app.mount("/api/images", StaticFiles(directory=IMAGE_DIR), name="images")


# --- Products -----------------------------------------------------------------

@app.get("/api/products")
def list_products() -> list[dict]:
    with connect_readonly() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    return [row_to_card(r, in_stock=r["total_stock"] > 0).model_dump() for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with connect_readonly() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    sizes = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return {**row_to_card(row).model_dump(exclude={"in_stock"}), "sizes": sizes}


# --- Chat ---------------------------------------------------------------------

HISTORY_FOR_AGENT = 20  # how many saved messages the agent gets to see
HISTORY_FOR_WIDGET = 50  # how many the chat widget reloads

# Each message costs a model call, so cap how fast one address can chat: 15 messages a minute.
_chat_times: dict[str, list[float]] = defaultdict(list)
CHAT_LIMIT, CHAT_WINDOW = 15, 60


def shopper_from_user(user: sqlite3.Row | None) -> ShopperInfo:
    """Who is chatting, taken from the login session. A guest has no name or email."""
    if user is None:
        return ShopperInfo(is_guest=True)
    return ShopperInfo(
        is_guest=False,
        user_id=user["id"],
        name=user["name"],
        first_name=user["first_name"] or user["name"].split()[0],
        email=user["email"],
    )


def _product_ids(products_json: str | None) -> list[str]:
    """chat_messages.products_json holds product ids (older rows hold full product dicts). Return just the ids."""
    try:
        items = json.loads(products_json or "[]")
    except json.JSONDecodeError:
        return []
    return [i if isinstance(i, str) else i.get("product_id", "") for i in items if isinstance(i, (str, dict))]


def load_saved_messages(conn: sqlite3.Connection, user_id: int, limit: int) -> list[SavedMessage]:
    """The newest `limit` messages of ONE user, oldest first. user_id always comes from the login session."""
    rows = conn.execute(
        """
        SELECT role, content, products_json, created_at FROM (
            SELECT id, role, content, products_json, created_at
            FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?
        ) ORDER BY id
        """,
        (user_id, limit),
    ).fetchall()
    return [
        SavedMessage(
            role=r["role"], content=r["content"], created_at=r["created_at"],
            products=cards_for([i for i in _product_ids(r["products_json"]) if i]),
        )
        for r in rows
    ]


def save_exchange(conn: sqlite3.Connection, user_id: int, question: str, reply: ChatReply) -> None:
    """Store the shopper's message and the agent's reply together (only ever called for logged-in shoppers)."""
    ids = json.dumps([p.product_id for p in reply.products]) if reply.products else None
    conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)", (user_id, question))
    conn.execute(
        "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
        (user_id, reply.message, ids),
    )


@app.get("/api/chat/history")
def chat_history(response: Response, cc_session: str | None = Cookie(default=None)) -> ChatHistory:
    """The logged-in shopper's saved chat. Guests have none."""
    response.headers["Cache-Control"] = "no-store"  # never let a browser or proxy reuse one user's history for another
    with connect() as conn:
        user = user_from_session(conn, cc_session)
        messages = load_saved_messages(conn, user["id"], HISTORY_FOR_WIDGET) if user else []
    return ChatHistory(messages=messages)


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request, cc_session: str | None = Cookie(default=None)) -> ChatReply:
    ip = request.client.host if request.client else "?"
    now = time.time()
    _chat_times[ip] = [t for t in _chat_times[ip] if now - t < CHAT_WINDOW]
    if len(_chat_times[ip]) >= CHAT_LIMIT:
        raise HTTPException(429, "You're chatting fast! Give me a moment and try again.")
    _chat_times[ip].append(now)

    # Safety: card numbers, passwords and similar are removed from what the shopper typed BEFORE the agent sees it
    # and before anything is saved, so they can't be used and can't end up in anyone's chat history.
    message, removed = redact_sensitive(body.message)

    # Who is chatting comes ONLY from the login cookie. Any name, email, or user id in the request body is ignored.
    with connect() as conn:
        user = user_from_session(conn, cc_session)
        shopper = shopper_from_user(user)
        if user:
            saved = load_saved_messages(conn, user["id"], HISTORY_FOR_AGENT)  # the agent's memory, from the database
            history = [m.model_copy(update={"content": redact_sensitive(m.content)[0]}) for m in saved]
        else:  # guests: only this page visit's conversation, which is never stored
            history = [ChatTurn(role=t.role, content=redact_sensitive(t.content)[0]) for t in body.history]

    try:
        reply = await run_chat(message, history, shopper, body.page, removed)
    except MissingApiKey as err:
        log.error("Chat is not configured: %s", err)
        raise HTTPException(503, "The shop assistant isn't set up yet.")
    except Exception:
        log.exception("Chat agent failed")
        raise HTTPException(502, "Sorry, I couldn't come up with an answer. Please try again.")

    if user:  # guests: nothing is saved
        with connect() as conn:
            save_exchange(conn, user["id"], message, reply)  # the cleaned message: never the card or password
    return reply
