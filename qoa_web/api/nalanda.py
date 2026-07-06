"""Nalanda community — learn, teach, discuss, invite (persisted in data/nalanda.json)."""

from __future__ import annotations

import json
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NALANDA_PATH = DATA_DIR / "nalanda.json"
SEED_PATH = DATA_DIR / "nalanda.seed.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time())}_{secrets.token_hex(3)}"


def _empty_store() -> dict[str, Any]:
    return {"lessons": [], "threads": [], "profile_invites": []}


def _load() -> dict[str, Any]:
    if NALANDA_PATH.is_file():
        try:
            data = json.loads(NALANDA_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("lessons", [])
                data.setdefault("threads", [])
                data.setdefault("profile_invites", [])
                return data
        except (json.JSONDecodeError, OSError):
            pass
    if SEED_PATH.is_file():
        try:
            data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                _save(data)
                return data
        except (json.JSONDecodeError, OSError):
            pass
    store = _empty_store()
    _save(store)
    return store


def _save(store: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NALANDA_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def reset_from_seed() -> None:
    if not SEED_PATH.is_file():
        _save(_empty_store())
        return
    data = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    _save(data)


def _normalize_profile_id(profile_id: str) -> str:
    pid = (profile_id or "").strip().lower()
    if not pid:
        raise ValueError("profile_id required")
    if not pid.startswith("p"):
        pid = f"p{pid}"
    return pid


def _resolve_author(profile_id: str, author_name: str = "") -> tuple[str, str]:
    from . import test_users as test_user_store

    pid = _normalize_profile_id(profile_id)
    try:
        persona = test_user_store.load_persona(pid)
    except FileNotFoundError as exc:
        raise ValueError(f"Unknown profile: {profile_id}") from exc
    name = (author_name or "").strip() or persona.get("name") or pid.upper()
    return pid, name


def list_lessons(limit: int = 50) -> list[dict[str, Any]]:
    store = _load()
    lessons = list(store.get("lessons") or [])
    lessons.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return lessons[: max(1, min(limit, 200))]


def add_lesson(
    profile_id: str,
    title: str,
    blurb: str = "",
    url: str = "",
    tags: list[str] | None = None,
    author_name: str = "",
) -> dict[str, Any]:
    title = (title or "").strip()
    if not title:
        raise ValueError("title required")
    pid, name = _resolve_author(profile_id, author_name)
    lesson = {
        "id": _new_id("lesson"),
        "author_profile_id": pid,
        "author_name": name,
        "title": title[:200],
        "url": (url or "").strip()[:500],
        "blurb": (blurb or "").strip()[:2000],
        "tags": [t.strip()[:40] for t in (tags or []) if t.strip()][:10],
        "created_at": _now_iso(),
    }
    store = _load()
    store.setdefault("lessons", []).insert(0, lesson)
    _save(store)
    return lesson


def list_threads(limit: int = 50) -> list[dict[str, Any]]:
    store = _load()
    threads = list(store.get("threads") or [])
    out = []
    for t in threads:
        replies = t.get("replies") or []
        out.append(
            {
                "id": t.get("id"),
                "author_profile_id": t.get("author_profile_id"),
                "author_name": t.get("author_name"),
                "title": t.get("title"),
                "body": t.get("body"),
                "created_at": t.get("created_at"),
                "reply_count": len(replies),
            }
        )
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out[: max(1, min(limit, 200))]


def get_thread(thread_id: str) -> dict[str, Any]:
    store = _load()
    for t in store.get("threads") or []:
        if t.get("id") == thread_id:
            return t
    raise ValueError("Thread not found")


def add_thread(
    profile_id: str,
    title: str,
    body: str,
    author_name: str = "",
) -> dict[str, Any]:
    title = (title or "").strip()
    body = (body or "").strip()
    if not title or not body:
        raise ValueError("title and body required")
    pid, name = _resolve_author(profile_id, author_name)
    thread = {
        "id": _new_id("thread"),
        "author_profile_id": pid,
        "author_name": name,
        "title": title[:200],
        "body": body[:8000],
        "created_at": _now_iso(),
        "replies": [],
    }
    store = _load()
    store.setdefault("threads", []).insert(0, thread)
    _save(store)
    return thread


def add_reply(
    thread_id: str,
    profile_id: str,
    body: str,
    author_name: str = "",
) -> dict[str, Any]:
    body = (body or "").strip()
    if not body:
        raise ValueError("body required")
    pid, name = _resolve_author(profile_id, author_name)
    reply = {
        "id": _new_id("reply"),
        "author_profile_id": pid,
        "author_name": name,
        "body": body[:4000],
        "created_at": _now_iso(),
    }
    store = _load()
    for t in store.get("threads") or []:
        if t.get("id") == thread_id:
            t.setdefault("replies", []).append(reply)
            _save(store)
            return {"thread_id": thread_id, "reply": reply}
    raise ValueError("Thread not found")


def get_or_create_profile_invite(profile_id: str, author_name: str = "") -> dict[str, Any]:
    """Personal Nalanda community invite — synced to invites.json for /welcome redeem."""
    from . import invites as invite_store

    pid, name = _resolve_author(profile_id, author_name)
    store = _load()
    invites_list = store.setdefault("profile_invites", [])
    existing = next((i for i in invites_list if i.get("owner_profile_id") == pid), None)
    if existing and existing.get("code"):
        code = existing["code"]
    else:
        token = secrets.token_hex(2).upper()
        code = f"QOA-NA1-{pid.upper().replace('P', '')}-{token}"
        entry = {
            "code": code,
            "owner_profile_id": pid,
            "owner_name": name,
            "created_at": _now_iso(),
            "redemption_count": 0,
        }
        if existing:
            existing.update(entry)
        else:
            invites_list.append(entry)
        _save(store)
        invite_store.register_nalanda_personal_code(code, pid, name)

    base = "/welcome"
    return {
        "code": code,
        "owner_profile_id": pid,
        "owner_name": name,
        "invite_path": f"{base}?code={code}",
        "share_text": (
            f"Join our free knowledge community on QA on Air — Nalanda. "
            f"Learn, teach, and discuss. Use my invite: {code}"
        ),
    }


def community_stats() -> dict[str, Any]:
    store = _load()
    threads = store.get("threads") or []
    replies = sum(len(t.get("replies") or []) for t in threads)
    return {
        "lesson_count": len(store.get("lessons") or []),
        "thread_count": len(threads),
        "reply_count": replies,
        "invite_count": len(store.get("profile_invites") or []),
    }
