"""User authentication — JWT + SQLite (PostgreSQL-ready via DATABASE_URL)."""

from __future__ import annotations

import json
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
UPLOADS_DIR = DATA_DIR / "uploads" / "profiles"
JWT_SECRET = os.environ.get("JWT_SECRET", "qoa-dev-change-me-in-production")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

VALID_AVATARS = frozenset({"creator", "qa_hunter", "nalanda", "promoter"})
VALID_ROLES = frozenset({"creator", "qa_hunter", "nalanda", "promoter", "both", "admin"})
SOCIAL_PROVIDERS = frozenset({"google", "facebook", "whatsapp", "instagram", "email"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT,
                name TEXT DEFAULT '',
                role TEXT DEFAULT 'creator',
                created_at TEXT NOT NULL
            )
            """
        )
        for col, decl in (
            ("first_name", "TEXT DEFAULT ''"),
            ("last_name", "TEXT DEFAULT ''"),
            ("country", "TEXT DEFAULT ''"),
            ("phone", "TEXT DEFAULT ''"),
            ("roles_json", "TEXT DEFAULT '[]'"),
            ("app_url", "TEXT DEFAULT ''"),
            ("profile_path", "TEXT DEFAULT ''"),
            ("social_provider", "TEXT DEFAULT ''"),
            ("social_id", "TEXT DEFAULT ''"),
            ("profile_complete", "INTEGER DEFAULT 0"),
        ):
            _ensure_column(conn, "users", col, decl)
        # Allow social users without password
        try:
            # SQLite cannot easily alter NOT NULL; new inserts use nullable password_hash
            pass
        except Exception:
            pass
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0
            )
            """
        )
        conn.commit()


def demo_allowed() -> bool:
    """Production sets QOA_ALLOW_DEMO=0 to block ?demo=1 invite bypass."""
    return os.environ.get("QOA_ALLOW_DEMO", "1").strip() not in ("0", "false", "False", "no")


def _parse_roles(raw: Any) -> list[str]:
    if isinstance(raw, list):
        roles = [str(r).strip() for r in raw if str(r).strip() in VALID_AVATARS]
        return roles
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return _parse_roles(data)
        except json.JSONDecodeError:
            pass
        if raw in VALID_AVATARS:
            return [raw]
        if raw == "both":
            return ["creator", "qa_hunter"]
    return []


def _primary_role(roles: list[str], fallback: str = "creator") -> str:
    if not roles:
        return fallback if fallback in VALID_ROLES else "creator"
    if "creator" in roles and "qa_hunter" in roles:
        return "both"
    if "qa_hunter" in roles:
        return "qa_hunter"
    if "nalanda" in roles:
        return "nalanda"
    if "promoter" in roles:
        return "promoter"
    if "creator" in roles:
        return "creator"
    return fallback


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    keys = row.keys()
    roles = _parse_roles(row["roles_json"] if "roles_json" in keys else "[]")
    if not roles:
        legacy = (row["role"] if "role" in keys else "creator") or "creator"
        if legacy == "both":
            roles = ["creator", "qa_hunter"]
        elif legacy in VALID_AVATARS:
            roles = [legacy]
        elif legacy == "admin":
            roles = ["creator", "qa_hunter", "nalanda"]
        else:
            roles = ["creator"]
    first = (row["first_name"] if "first_name" in keys else "") or ""
    last = (row["last_name"] if "last_name" in keys else "") or ""
    name = (row["name"] if "name" in keys else "") or ""
    if not name:
        name = f"{first} {last}".strip()
    return {
        "id": row["id"],
        "email": row["email"],
        "name": name,
        "first_name": first,
        "last_name": last,
        "country": (row["country"] if "country" in keys else "") or "",
        "phone": (row["phone"] if "phone" in keys else "") or "",
        "role": row["role"] if "role" in keys else "creator",
        "roles": roles,
        "app_url": (row["app_url"] if "app_url" in keys else "") or "",
        "profile_path": (row["profile_path"] if "profile_path" in keys else "") or "",
        "social_provider": (row["social_provider"] if "social_provider" in keys else "") or "",
        "profile_complete": bool(row["profile_complete"]) if "profile_complete" in keys else True,
        "created_at": row["created_at"],
    }


def register_user(
    email: str,
    password: str | None = None,
    name: str = "",
    role: str = "creator",
    *,
    first_name: str = "",
    last_name: str = "",
    country: str = "",
    phone: str = "",
    roles: list[str] | None = None,
    app_url: str = "",
    social_provider: str = "",
    social_id: str = "",
    profile_complete: bool = False,
) -> dict[str, Any]:
    init_db()
    email = email.strip().lower()
    if not email:
        raise ValueError("Email required")
    if not social_provider and (not password or len(password) < 8):
        raise ValueError("Password must be at least 8 characters")
    role_list = _parse_roles(roles) if roles is not None else []
    if not role_list and role:
        if role == "both":
            role_list = ["creator", "qa_hunter"]
        elif role in VALID_AVATARS:
            role_list = [role]
    if not role_list:
        role_list = ["creator"]
    primary = _primary_role(role_list, role if role in VALID_ROLES else "creator")
    full_name = name.strip() or f"{first_name.strip()} {last_name.strip()}".strip()
    uid = uuid.uuid4().hex
    if password:
        pw_hash = pwd_context.hash(password)
    else:
        # Social / passwordless: random hash so password login fails until reset
        pw_hash = pwd_context.hash(uuid.uuid4().hex + uuid.uuid4().hex)
    with _connect() as conn:
        try:
            conn.execute(
                """
                INSERT INTO users (
                    id, email, password_hash, name, role, created_at,
                    first_name, last_name, country, phone, roles_json,
                    app_url, social_provider, social_id, profile_complete
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uid,
                    email,
                    pw_hash,
                    full_name,
                    primary,
                    _now(),
                    first_name.strip(),
                    last_name.strip(),
                    country.strip(),
                    phone.strip(),
                    json.dumps(role_list),
                    app_url.strip(),
                    social_provider.strip(),
                    social_id.strip(),
                    1 if profile_complete else 0,
                ),
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
    if not row:
        return None
    pw_hash = row["password_hash"]
    if not pw_hash or not pwd_context.verify(password, pw_hash):
        return None
    return _row_to_user(row)


def social_login_or_register(provider: str, email: str, name: str = "") -> dict[str, Any]:
    """Local/dev social stub — real OAuth tokens can replace this later."""
    provider = (provider or "").strip().lower()
    if provider not in SOCIAL_PROVIDERS or provider == "email":
        raise ValueError("Unsupported social provider")
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Email required for social sign-in")
    init_db()
    existing = get_user_by_email(email)
    if existing:
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET social_provider = ?, social_id = COALESCE(NULLIF(social_id,''), ?) WHERE id = ?",
                (provider, f"{provider}:{email}", existing["id"]),
            )
            conn.commit()
        user = get_user(existing["id"])
        if not user:
            raise ValueError("Social login failed")
        return user
    parts = name.strip().split(None, 1) if name.strip() else []
    return register_user(
        email=email,
        password=None,
        name=name.strip(),
        first_name=parts[0] if parts else "",
        last_name=parts[1] if len(parts) > 1 else "",
        social_provider=provider,
        social_id=f"{provider}:{email}",
        profile_complete=False,
        roles=["creator"],
    )


def update_user_profile(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    init_db()
    user = get_user(user_id)
    if not user:
        raise ValueError("User not found")
    first_name = str(patch.get("first_name", user.get("first_name") or "")).strip()
    last_name = str(patch.get("last_name", user.get("last_name") or "")).strip()
    country = str(patch.get("country", user.get("country") or "")).strip()
    phone = str(patch.get("phone", user.get("phone") or "")).strip()
    app_url = str(patch.get("app_url", user.get("app_url") or "")).strip()
    roles = _parse_roles(patch.get("roles", user.get("roles")))
    if not roles:
        roles = user.get("roles") or ["creator"]
    primary = _primary_role(roles)
    name = f"{first_name} {last_name}".strip() or user.get("name") or ""
    profile_path = str(patch.get("profile_path", user.get("profile_path") or "")).strip()
    complete = patch.get("profile_complete")
    if complete is None:
        complete = bool(first_name and last_name and roles)
    with _connect() as conn:
        conn.execute(
            """
            UPDATE users SET
                name = ?, first_name = ?, last_name = ?, country = ?, phone = ?,
                roles_json = ?, role = ?, app_url = ?, profile_path = ?, profile_complete = ?
            WHERE id = ?
            """,
            (
                name,
                first_name,
                last_name,
                country,
                phone,
                json.dumps(roles),
                primary,
                app_url,
                profile_path,
                1 if complete else 0,
                user_id,
            ),
        )
        conn.commit()
    updated = get_user(user_id)
    if not updated:
        raise ValueError("Update failed")
    return updated


def save_profile_upload(user_id: str, filename: str, data: bytes) -> str:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in Path(filename).name if c.isalnum() or c in "._-") or "profile.bin"
    dest = UPLOADS_DIR / f"{user_id}_{safe}"
    dest.write_bytes(data)
    rel = f"profiles/{dest.name}"
    update_user_profile(user_id, {"profile_path": rel})
    return rel


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
        "roles": user.get("roles") or [],
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


def get_user_by_email(email: str) -> dict[str, Any] | None:
    init_db()
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _row_to_user(row) if row else None


def create_password_reset(email: str) -> str | None:
    """Return reset token if user exists; always opaque to callers for privacy."""
    user = get_user_by_email(email)
    if not user:
        return None
    token = uuid.uuid4().hex
    expires = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO password_resets (token, user_id, expires_at, used) VALUES (?, ?, ?, 0)",
            (token, user["id"], expires),
        )
        conn.commit()
    return token


def reset_password(token: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValueError("Password must be at least 8 characters")
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token = ? AND used = 0", (token,)
        ).fetchone()
        if not row:
            raise ValueError("Invalid or expired reset token")
        exp = datetime.fromisoformat(row["expires_at"])
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise ValueError("Invalid or expired reset token")
        pw_hash = pwd_context.hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (pw_hash, row["user_id"]),
        )
        conn.execute("UPDATE password_resets SET used = 1 WHERE token = ?", (token,))
        conn.commit()
