"""Waitlist storage for hybrid MVP — email capture before real auth."""

from __future__ import annotations

import csv
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WAITLIST_PATH = DATA_DIR / "waitlist.json"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_ROLES = frozenset({"creator", "consultant", "networker", "any"})
_RATE: dict[str, list[float]] = {}
_RATE_WINDOW_SEC = 60.0
_RATE_MAX = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _load() -> list[dict[str, Any]]:
    if not WAITLIST_PATH.is_file():
        return []
    try:
        data = json.loads(WAITLIST_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WAITLIST_PATH.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _rate_limit_key(email: str, ip: str | None) -> str:
    return (ip or "local") + ":" + email.lower()


def check_rate_limit(email: str, ip: str | None = None) -> None:
    key = _rate_limit_key(email, ip)
    now = time.time()
    hits = [t for t in _RATE.get(key, []) if now - t < _RATE_WINDOW_SEC]
    if len(hits) >= _RATE_MAX:
        raise ValueError("Too many requests — try again in a minute")
    hits.append(now)
    _RATE[key] = hits


def add_entry(
    email: str,
    role: str = "any",
    note: str = "",
    source: str = "signin",
    ip: str | None = None,
) -> dict[str, Any]:
    email = (email or "").strip().lower()
    if not email or not EMAIL_RE.match(email):
        raise ValueError("Valid email required")
    role = (role or "any").strip().lower()
    if role not in VALID_ROLES:
        role = "any"
    note = (note or "").strip()[:500]
    source = (source or "signin").strip()[:64]

    check_rate_limit(email, ip)

    entries = _load()
    for e in entries:
        if e.get("email", "").lower() == email:
            return {"entry": e, "duplicate": True, "count": len(entries)}

    entry = {
        "id": f"wl_{int(time.time())}_{len(entries) + 1}",
        "email": email,
        "role": role,
        "note": note,
        "source": source,
        "created_at": _now_iso(),
    }
    entries.append(entry)
    _save(entries)
    return {"entry": entry, "duplicate": False, "count": len(entries)}


def list_entries() -> list[dict[str, Any]]:
    return _load()


def count_entries() -> int:
    return len(_load())


def export_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "email", "role", "note", "source", "created_at"])
    for e in _load():
        w.writerow([
            e.get("id", ""),
            e.get("email", ""),
            e.get("role", ""),
            e.get("note", ""),
            e.get("source", ""),
            e.get("created_at", ""),
        ])
    return buf.getvalue()
