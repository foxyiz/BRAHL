"""User authentication — JWT + SQLite (PostgreSQL-ready via DATABASE_URL)."""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from passlib.context import CryptContext

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "users.db"
JWT_SECRET = os.environ.get("JWT_SECRET", "qoa-dev-change-me-in-production")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT DEFAULT '',
                role TEXT DEFAULT 'creator',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"] or "",
        "role": row["role"] or "creator",
        "created_at": row["created_at"],
    }


def register_user(email: str, password: str, name: str = "", role: str = "creator") -> dict[str, Any]:
    init_db()
    email = email.strip().lower()
    if not email or not password:
        raise ValueError("Email and password required")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if role not in ("creator", "qa_hunter", "both", "admin"):
        role = "creator"
    uid = uuid.uuid4().hex
    pw_hash = pwd_context.hash(password)
    with _connect() as conn:
        try:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (uid, email, pw_hash, name.strip(), role, _now()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("Email already registered") from None
    user = get_user(uid)
    if not user:
        raise ValueError("Registration failed")
    return user


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    init_db()
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row or not pwd_context.verify(password, row["password_hash"]):
        return None
    return _row_to_user(row)


def get_user(user_id: str) -> dict[str, Any] | None:
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _row_to_user(row) if row else None


def create_token(user: dict[str, Any]) -> str:
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "creator"),
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except jwt.PyJWTError:
        return None


def user_from_request(authorization: str | None) -> dict[str, Any] | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    return get_user(str(payload["sub"]))
