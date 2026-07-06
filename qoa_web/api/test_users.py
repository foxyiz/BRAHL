"""Fictional test user personas — loaded from Docs/test-user-data/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]
TEST_USER_DATA_DIR = KK_ROOT / "Docs" / "test-user-data"
INDEX_PATH = TEST_USER_DATA_DIR / "index.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def load_index() -> dict[str, Any]:
    return _load_json(INDEX_PATH)


def persona_path(persona_id: str) -> Path:
    idx = load_index()
    pid = persona_id.lower()
    if not pid.startswith("p"):
        pid = f"p{pid}"
    for entry in idx.get("personas", []):
        if entry.get("id") == pid:
            return TEST_USER_DATA_DIR / entry["file"]
    raise FileNotFoundError(f"Unknown persona: {persona_id}")


def load_persona(persona_id: str) -> dict[str, Any]:
    data = _load_json(persona_path(persona_id))
    data["_source"] = str(persona_path(persona_id).relative_to(KK_ROOT)).replace("\\", "/")
    return data


def list_personas() -> list[dict[str, Any]]:
    idx = load_index()
    out: list[dict[str, Any]] = []
    for entry in idx.get("personas", []):
        path = TEST_USER_DATA_DIR / entry["file"]
        exists = path.is_file()
        summary: dict[str, Any] = {
            "id": entry["id"],
            "code": entry.get("code", entry["id"].upper()),
            "file": entry["file"],
            "ypad_design_column": entry.get("ypad_design_column"),
            "exists": exists,
        }
        if exists:
            p = _load_json(path)
            summary.update(
                {
                    "name": p.get("name"),
                    "title": p.get("title"),
                    "default_avatar": p.get("default_avatar"),
                    "allowed_avatars": p.get("allowed_avatars", []),
                    "role": p.get("role"),
                }
            )
        out.append(summary)
    return out


def tasks_for_avatar(persona: dict[str, Any], avatar: str) -> list[dict[str, Any]]:
    if avatar == "consultant":
        return list(persona.get("hitl_tasks") or [])
    if avatar == "networker":
        return list(persona.get("networker_tasks") or _default_networker_tasks())
    tasks = list(persona.get("client_tasks") or [])
    if persona.get("admin"):
        tasks = tasks + list(persona.get("admin_tasks") or [])
    return tasks


def _default_networker_tasks() -> list[dict[str, Any]]:
    return [
        {"phase": "nalanda", "title": "Browse Learn — featured paths", "detail": "Open Nalanda SkillFlow AI or ITelearn links."},
        {"phase": "nalanda", "title": "Teach — share a lesson", "detail": "Post a title, link, and blurb for the community."},
        {"phase": "nalanda", "title": "Discuss — reply in a thread", "detail": "Join the welcome thread or start your own."},
        {"phase": "nalanda", "title": "Invite — copy your community link", "detail": "Share your personal invite with friends."},
    ]


def fixture_bundle(persona_id: str) -> dict[str, Any]:
    p = load_persona(persona_id)
    return {
        "persona_id": p["id"],
        "code": p.get("code"),
        "name": p.get("name"),
        "fictional": True,
        "default_avatar": p.get("default_avatar"),
        "allowed_avatars": p.get("allowed_avatars", []),
        "ai": p.get("ai", {}),
        "sample_data": p.get("sample_data", {}),
        "client_tasks": p.get("client_tasks", []),
        "hitl_tasks": p.get("hitl_tasks", []),
        "networker_tasks": p.get("networker_tasks", []),
        "admin_tasks": p.get("admin_tasks", []),
        "ypad_design_column": p.get("ypad_design_column"),
        "verify_tags": p.get("verify_tags", []),
        "profile_url": f"http://127.0.0.1:8765/?profile={p['id']}&suite=qoa_web",
        "source": p.get("_source"),
    }


def to_frontend_profile(p: dict[str, Any]) -> dict[str, Any]:
    """Shape for profiles.js / sign-in UI."""
    ai = p.get("ai") or {}
    allowed = p.get("allowed_avatars") or []
    return {
        "id": p["id"],
        "code": p.get("code"),
        "name": p.get("name"),
        "title": p.get("title"),
        "role": p.get("role"),
        "defaultAvatar": p.get("default_avatar", "client"),
        "aiDefault": ai.get("default", True),
        "aiLocked": ai.get("locked", False),
        "dualRole": bool(p.get("dual_role")),
        "admin": bool(p.get("admin")),
        "techLevel": p.get("tech_level"),
        "consultantTier": p.get("consultant_tier"),
        "allowedAvatars": allowed,
        "landing": p.get("landing", "app"),
        "accent": p.get("accent", "client"),
        "blurb": p.get("blurb", ""),
        "journey": p.get("journey") or [],
        "ypadDesignColumn": p.get("ypad_design_column"),
        "firstVisit": bool(p.get("first_visit")),
        "fictional": True,
    }


def all_frontend_profiles() -> list[dict[str, Any]]:
    idx = load_index()
    profiles: list[dict[str, Any]] = []
    for entry in idx.get("personas", []):
        path = TEST_USER_DATA_DIR / entry["file"]
        if path.is_file():
            profiles.append(to_frontend_profile(_load_json(path)))
    return profiles
