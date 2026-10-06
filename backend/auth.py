"""Account creation, login, and sessions for Campus Customs.

Passwords are hashed with Argon2id (salted automatically) and the hash never leaves
the server. Logged-in browsers hold a random session token in an httpOnly cookie;
only a SHA-256 of that token is stored in the database.
"""

import hashlib
import re
import secrets
import sqlite3
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs.db"

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7

RESIDENTIAL_COLLEGES = [
    "Benjamin Franklin", "Berkeley", "Branford", "Davenport", "Ezra Stiles",
    "Grace Hopper", "Jonathan Edwards", "Morse", "Pauli Murray", "Pierson",
    "Saybrook", "Silliman", "Timothy Dwight", "Trumbull",
]
GRADUATE_SCHOOLS = [
    "Graduate School of Arts and Sciences", "School of Architecture", "School of Art",
    "School of the Environment", "School of Drama", "School of Engineering & Applied Science",
    "Divinity School", "Law School", "School of Management", "School of Medicine",
    "School of Music", "School of Nursing", "School of Public Health",
    "Jackson School of Global Affairs",
]
ALL_AFFILIATIONS = RESIDENTIAL_COLLEGES + GRADUATE_SCHOOLS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api/auth", tags=["auth"])
hasher = PasswordHasher()  # Argon2id with library-default (OWASP-grade) cost settings

# Hash used to burn the same CPU time when an email is unknown, so response time
# doesn't reveal which emails have accounts.
_DUMMY_HASH = hasher.hash("not-a-real-password")


# ---------- database ----------

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema() -> None:
    """Add the pieces the app needs to the existing database schema (safe to run every start)."""
    with connect() as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(users)")]
        if "residential_college" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN residential_college TEXT")
        # How an item is cut: 'fitted', 'regular', or 'oversized'. Empty (NULL) means we don't know.
        catalogue_cols = [r["name"] for r in conn.execute("PRAGMA table_info(catalogue)")]
        if "fit" not in catalogue_cols:
            conn.execute("ALTER TABLE catalogue ADD COLUMN fit TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )
        # Chat history is always read one user at a time, newest first.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


# ---------- request models (server-side validation) ----------

class SignupBody(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str
    residential_college: str

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name can't be blank")
        return v

    @field_validator("email")
    @classmethod
    def clean_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("residential_college")
    @classmethod
    def known_affiliation(cls, v: str) -> str:
        if v not in ALL_AFFILIATIONS:
            raise ValueError("Pick a residential college or school from the list")
        return v


class LoginBody(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


# ---------- helpers ----------

def public_user(row: sqlite3.Row) -> dict:
    """The only shape of a user the API ever returns. No password_hash, ever."""
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "residential_college": row["residential_college"],
    }


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(response: Response, conn: sqlite3.Connection, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (datetime.now(timezone.utc).isoformat(),))
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires.isoformat()),
    )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_DAYS * 86400,
        httponly=True, samesite="lax", secure=False,  # secure=True once served over HTTPS
        path="/",
    )


def user_from_session(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        """
        SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > ?
        """,
        (_token_hash(token), datetime.now(timezone.utc).isoformat()),
    ).fetchone()


# Simple brute-force brake: 5 failed logins per email+IP per 5 minutes.
_failures: dict[str, list[float]] = defaultdict(list)
_WINDOW, _MAX_FAILS = 300, 5


def _throttle_key(email: str, request: Request) -> str:
    return f"{email}|{request.client.host if request.client else '?'}"


def _recent_failures(key: str) -> list[float]:
    now = time.time()
    _failures[key] = [t for t in _failures[key] if now - t < _WINDOW]
    return _failures[key]


# ---------- routes ----------

@router.get("/options")
def options() -> dict:
    return {"residential_colleges": RESIDENTIAL_COLLEGES, "graduate_schools": GRADUATE_SCHOOLS}


@router.post("/signup", status_code=201)
def signup(body: SignupBody, response: Response) -> dict:
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords don't match")

    password_hash = hasher.hash(body.password)
    with connect() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users (name, first_name, last_name, email, password_hash, residential_college)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    f"{body.first_name} {body.last_name}", body.first_name, body.last_name,
                    body.email, password_hash, body.residential_college,
                ),
            )
        except sqlite3.IntegrityError:  # users.email is UNIQUE
            raise HTTPException(409, "An account with that email already exists")
        user_id = cur.lastrowid
        start_session(response, conn, user_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": public_user(row)}


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    email = body.email.strip().lower()
    key = _throttle_key(email, request)
    if len(_recent_failures(key)) >= _MAX_FAILS:
        raise HTTPException(429, "Too many attempts. Try again in a few minutes.")

    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        stored = row["password_hash"] if row else _DUMMY_HASH
        try:
            hasher.verify(stored, body.password)
            ok = row is not None
        except (VerificationError, InvalidHashError):
            # InvalidHashError covers older accounts seeded with a non-Argon2 hash format.
            ok = False

        if not ok:
            _failures[key].append(time.time())
            raise HTTPException(401, "Incorrect email or password")

        _failures.pop(key, None)
        if hasher.check_needs_rehash(row["password_hash"]):
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hasher.hash(body.password), row["id"]),
            )
        start_session(response, conn, row["id"])
    return {"user": public_user(row)}


@router.get("/me")
def me(cc_session: str | None = Cookie(default=None)) -> dict:
    with connect() as conn:
        row = user_from_session(conn, cc_session)
    return {"user": public_user(row) if row else None}


@router.post("/logout", status_code=204)
def logout(response: Response, cc_session: str | None = Cookie(default=None)) -> None:
    if cc_session:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(cc_session),))
    response.delete_cookie(SESSION_COOKIE, path="/")
