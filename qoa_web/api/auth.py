"""User authentication — JWT + SQLite (PostgreSQL-ready via DATABASE_URL)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from passlib.context import CryptContext

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "users.db"
UPLOADS_DIR = DATA_DIR / "uploads" / "profiles"
KK_ROOT = Path(__file__).resolve().parent.parent.parent
FOXYIZ_F = KK_ROOT / "FoXYiZ" / "f"


def _load_env_files() -> None:
    """Load KK/.env then FoXYiZ/f/.env (do not override existing process env)."""
    for env_path in (KK_ROOT / ".env", FOXYIZ_F / ".env"):
        if not env_path.is_file():
            continue
        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
        except OSError:
            pass


_load_env_files()

JWT_SECRET = os.environ.get("JWT_SECRET", "qoa-dev-change-me-in-production")
JWT_ALG = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "168"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Arena avatars (BRAHL session)
VALID_AVATARS = frozenset({"creator", "qa_hunter", "nalanda", "promoter"})
# Soft personas (chips only in V1)
PERSONA_ROLES = frozenset({"trainer", "student"})
# Platform privilege roles
PRIVILEGE_ROLES = frozenset({"admin", "super_admin"})
# All roles allowed in roles_json
ALL_PROFILE_ROLES = VALID_AVATARS | PERSONA_ROLES | PRIVILEGE_ROLES
VALID_ROLES = frozenset({"creator", "qa_hunter", "nalanda", "promoter", "both", "admin", "super_admin"})
SOCIAL_PROVIDERS = frozenset({"google", "facebook", "instagram", "email"})

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _google_client_id() -> str:
    return os.environ.get("GOOGLE_CLIENT_ID", "").strip()


def _google_client_secret() -> str:
    return os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()


def _app_base_url() -> str:
    return os.environ.get("APP_BASE_URL", "http://127.0.0.1:8765").rstrip("/")


def google_oauth_configured() -> bool:
    return bool(_google_client_id() and _google_client_secret())


def auth_providers() -> dict[str, Any]:
    return {
        "google": google_oauth_configured(),
        "facebook": False,
        "instagram": False,
        "email": True,
    }


def google_redirect_uri() -> str:
    return f"{_app_base_url()}/api/auth/google/callback"


def make_oauth_state(next_path: str = "/signup") -> str:
    """Signed CSRF state: timestamp:next:sig (no server session store)."""
    next_path = next_path if next_path.startswith("/") else "/signup"
    if next_path not in ("/signup", "/login", "/app"):
        next_path = "/signup"
    payload = f"{int(time.time())}:{next_path}"
    sig = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:20]
    raw = f"{payload}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def parse_oauth_state(state: str, *, max_age_sec: int = 600) -> str:
    try:
        pad = "=" * (-len(state) % 4)
        raw = base64.urlsafe_b64decode(state + pad).decode()
        ts_s, next_path, sig = raw.split(":", 2)
        payload = f"{ts_s}:{next_path}"
        expect = hmac.new(JWT_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()[:20]
        if not hmac.compare_digest(sig, expect):
            raise ValueError("Invalid OAuth state")
        if abs(time.time() - int(ts_s)) > max_age_sec:
            raise ValueError("OAuth state expired")
        if next_path not in ("/signup", "/login", "/app"):
            return "/signup"
        return next_path
    except Exception as exc:
        raise ValueError("Invalid OAuth state") from exc


def google_authorize_url(state: str) -> str:
    if not google_oauth_configured():
        raise ValueError("Google OAuth is not configured")
    q = urllib.parse.urlencode(
        {
            "client_id": _google_client_id(),
            "redirect_uri": google_redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state,
        }
    )
    return f"{GOOGLE_AUTH_URL}?{q}"


def _http_json(method: str, url: str, *, data: dict[str, str] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Accept", "application/json")
    if body is not None:
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:300]
        raise ValueError(f"Google OAuth failed ({exc.code}): {detail}") from exc


def exchange_google_code(code: str) -> dict[str, Any]:
    """Exchange auth code → userinfo {email, name, given_name, family_name, sub}."""
    if not google_oauth_configured():
        raise ValueError("Google OAuth is not configured")
    token = _http_json(
        "POST",
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": _google_client_id(),
            "client_secret": _google_client_secret(),
            "redirect_uri": google_redirect_uri(),
            "grant_type": "authorization_code",
        },
    )
    access = token.get("access_token")
    if not access:
        raise ValueError("Google did not return an access token")
    info = _http_json(
        "GET",
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access}"},
    )
    email = (info.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Google account has no email")
    return {
        "email": email,
        "name": (info.get("name") or "").strip(),
        "given_name": (info.get("given_name") or "").strip(),
        "family_name": (info.get("family_name") or "").strip(),
        "sub": str(info.get("sub") or ""),
    }


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
            ("city", "TEXT DEFAULT ''"),
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
        roles = [str(r).strip() for r in raw if str(r).strip() in ALL_PROFILE_ROLES]
        # preserve order, unique
        seen: list[str] = []
        for r in roles:
            if r not in seen:
                seen.append(r)
        return seen
    if isinstance(raw, str) and raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return _parse_roles(data)
        except json.JSONDecodeError:
            pass
        if raw in ALL_PROFILE_ROLES:
            return [raw]
        if raw == "both":
            return ["creator", "qa_hunter"]
    return []


def _primary_role(roles: list[str], fallback: str = "creator") -> str:
    if not roles:
        return fallback if fallback in VALID_ROLES else "creator"
    if "super_admin" in roles:
        return "super_admin"
    if "admin" in roles:
        return "admin"
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
    if "trainer" in roles:
        return "trainer"
    if "student" in roles:
        return "student"
    return fallback


def has_privilege(user: dict[str, Any] | None, *, level: str = "admin") -> bool:
    """level: admin | super_admin — super_admin implies admin."""
    if not user:
        return False
    roles = set(user.get("roles") or [])
    primary = (user.get("role") or "").strip()
    if level == "super_admin":
        return "super_admin" in roles or primary == "super_admin"
    return bool(roles & PRIVILEGE_ROLES) or primary in ("admin", "super_admin")


def is_platform_admin(user: dict[str, Any] | None) -> bool:
    return has_privilege(user, level="admin")


def is_super_admin(user: dict[str, Any] | None) -> bool:
    return has_privilege(user, level="super_admin")


def _row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    keys = row.keys()
    roles = _parse_roles(row["roles_json"] if "roles_json" in keys else "[]")
    if not roles:
        legacy = (row["role"] if "role" in keys else "creator") or "creator"
        if legacy == "both":
            roles = ["creator", "qa_hunter"]
        elif legacy in VALID_AVATARS:
            roles = [legacy]
        elif legacy == "super_admin":
            roles = ["super_admin", "creator", "qa_hunter", "nalanda"]
        elif legacy == "admin":
            roles = ["admin", "creator", "qa_hunter", "nalanda"]
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
        "city": (row["city"] if "city" in keys else "") or "",
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
    city: str = "",
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
                    first_name, last_name, country, city, phone, roles_json,
                    app_url, social_provider, social_id, profile_complete
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    city.strip(),
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


def social_login_or_register(
    provider: str,
    email: str,
    name: str = "",
    *,
    social_id: str = "",
    first_name: str = "",
    last_name: str = "",
) -> dict[str, Any]:
    """Register or sign in via an OAuth provider (Google) or legacy email stub."""
    provider = (provider or "").strip().lower()
    if provider not in SOCIAL_PROVIDERS or provider == "email":
        raise ValueError("Unsupported social provider")
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Email required for social sign-in")
    init_db()
    sid = (social_id or f"{provider}:{email}").strip()
    existing = get_user_by_email(email)
    if existing:
        with _connect() as conn:
            conn.execute(
                "UPDATE users SET social_provider = ?, social_id = COALESCE(NULLIF(social_id,''), ?) WHERE id = ?",
                (provider, sid, existing["id"]),
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
        first_name=first_name or (parts[0] if parts else ""),
        last_name=last_name or (parts[1] if len(parts) > 1 else ""),
        social_provider=provider,
        social_id=sid,
        profile_complete=False,
        roles=["creator"],
    )


def login_with_google_profile(info: dict[str, Any]) -> dict[str, Any]:
    return social_login_or_register(
        "google",
        info["email"],
        info.get("name") or "",
        social_id=f"google:{info.get('sub') or info['email']}",
        first_name=info.get("given_name") or "",
        last_name=info.get("family_name") or "",
    )


def update_user_profile(user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    init_db()
    user = get_user(user_id)
    if not user:
        raise ValueError("User not found")
    first_name = str(patch.get("first_name", user.get("first_name") or "")).strip()
    last_name = str(patch.get("last_name", user.get("last_name") or "")).strip()
    country = str(patch.get("country", user.get("country") or "")).strip()
    city = str(patch.get("city", user.get("city") or "")).strip()
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
                name = ?, first_name = ?, last_name = ?, country = ?, city = ?, phone = ?,
                roles_json = ?, role = ?, app_url = ?, profile_path = ?, profile_complete = ?
            WHERE id = ?
            """,
            (
                name,
                first_name,
                last_name,
                country,
                city,
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


def list_users() -> list[dict[str, Any]]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    return [_row_to_user(r) for r in rows]


def set_user_roles(
    user_id: str,
    new_roles: list[str],
    *,
    actor: dict[str, Any],
) -> dict[str, Any]:
    """Platform admin updates another user's roles_json. Only super_admin can grant/revoke super_admin."""
    target = get_user(user_id)
    if not target:
        raise ValueError("User not found")
    if not is_platform_admin(actor):
        raise PermissionError("Platform admin required")
    roles = _parse_roles(new_roles)
    if not roles:
        roles = ["creator"]
    actor_is_super = is_super_admin(actor)
    target_was_super = is_super_admin(target)
    becoming_super = "super_admin" in roles
    if becoming_super and not actor_is_super:
        raise PermissionError("Only super admin can grant super_admin")
    if target_was_super and not becoming_super and not actor_is_super:
        raise PermissionError("Only super admin can revoke super_admin")
    if "admin" in roles and not actor_is_super and not is_platform_admin(actor):
        raise PermissionError("Cannot grant admin")
    # Non-super admin cannot grant admin to others (plan: Super can grant Admin; Admin cannot mint Super)
    if "admin" in roles and "admin" not in (target.get("roles") or []) and not actor_is_super:
        raise PermissionError("Only super admin can grant admin")
    return update_user_profile(user_id, {"roles": roles, "profile_complete": True})
