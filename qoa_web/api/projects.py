"""Local project store for qoa_web avatar Build flows."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROJECTS_FILE = DATA_DIR / "projects.json"
UPLOADS_DIR = DATA_DIR / "uploads"

HITL_CONSULTANT_ID = "local-hitl-consultant"
from paths import KK_ROOT, Z_DIR, resolve_repo

REPORT_SOURCE_LABELS = {
    "automation": "Automation",
    "automation_ai": "Automation + AI",
    "human_in_the_loop": "QA Hunter",
    "human_ai": "QA Hunter + AI",
    "human_automation": "QA Hunter + Automation",
}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    if not PROJECTS_FILE.is_file():
        PROJECTS_FILE.write_text("[]", encoding="utf-8")


def _normalize(project: dict[str, Any]) -> dict[str, Any]:
    """Backfill fields for older project records."""
    project.setdefault("purpose", project.get("prompt", ""))
    project.setdefault("chat_messages", [])
    project.setdefault("context_items", [])
    project.setdefault("budget_usd", 0.0)
    project.setdefault("budget_split", {"automation_pct": 50, "human_pct": 50})
    project.setdefault("hitl_consultants", [])
    project.setdefault("brahl_chat_messages", [])
    project.setdefault("team_messages", [])
    project.setdefault("team_tasks", [])
    project.setdefault("documents", [])
    project.setdefault("atomic77_chat_messages", [])
    project.setdefault("atomic77_usage", {"messages": 0, "tokens_est": 0, "user_messages": 0})
    project.setdefault("ai_enabled", True)
    project.setdefault("cycle_history", [])
    project.setdefault("suite_name", "")
    project.setdefault("suite_config", "")
    project.setdefault("hitl_stories", [])
    project.setdefault("hitl_invites", [])
    project.setdefault("change_requests", [])
    project.setdefault("runtime_mode", "local")
    project.setdefault("app_version", "")
    project.setdefault("baseline_version", "")
    project.setdefault("baseline_run", None)
    project.setdefault("owner_user_id", None)
    project.setdefault("brahl_plan_draft", None)
    project.setdefault("ai_usage", {"calls": 0, "total_tokens": 0, "usd_est": 0.0})
    project.setdefault("evidence_library", [])
    if not project.get("chat_messages"):
        project["chat_messages"] = [
            {
                "id": "welcome",
                "role": "assistant",
                "text": "Hi — I'm your BRAHL Build assistant. What are you trying to test or improve?",
                "at": project.get("created_at") or _now(),
            }
        ]
    if not project.get("brahl_chat_messages"):
        project["brahl_chat_messages"] = [
            {
                "id": "brahl-welcome",
                "role": "assistant",
                "text": "I'm the BRAHL model for this project. Select a report or ask about the latest BRAHL findings.",
                "at": project.get("created_at") or _now(),
            }
        ]
    if not project.get("atomic77_chat_messages"):
        project["atomic77_chat_messages"] = [
            {
                "id": "a77-welcome",
                "role": "assistant",
                "text": (
                    "I'm **Atomic 77** — idea to launch inside QA on Air. "
                    "Ask about scope, BRAHL, launch, costs, or QA Hunter workflows. "
                    "Toggle **AI on** for full assistant mode."
                ),
                "at": project.get("created_at") or _now(),
            }
        ]
    if not project.get("prompt") and project.get("purpose"):
        project["prompt"] = project["purpose"]
    if not project.get("suite_name"):
        name_l = (project.get("name") or "").lower()
        url_l = (project.get("app_url") or "").lower()
        for suite in ("qoa_web", "sunshine", "qoa2", "ivvu", "atomic77"):
            if suite in name_l or suite in url_l:
                project["suite_name"] = suite
                project.setdefault("suite_config", f"y/{suite}/{suite}.json")
                break
    return project


def load_projects() -> list[dict[str, Any]]:
    _ensure_dirs()
    try:
        data = json.loads(PROJECTS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [_normalize(dict(p)) for p in data]


def save_projects(projects: list[dict[str, Any]]) -> None:
    _ensure_dirs()
    PROJECTS_FILE.write_text(json.dumps(projects, indent=2), encoding="utf-8")


def get_project(project_id: str) -> dict[str, Any] | None:
    for p in load_projects():
        if p.get("id") == project_id:
            return p
    return None


def list_client_projects(owner_user_id: str | None = None) -> list[dict[str, Any]]:
    items = [p for p in load_projects() if p.get("owner_avatar") == "client"]
    if owner_user_id:
        items = [
            p
            for p in items
            if p.get("owner_user_id") == owner_user_id or not p.get("owner_user_id")
        ]
    return items


def list_consultant_projects() -> list[dict[str, Any]]:
    return [
        p
        for p in load_projects()
        if p.get("owner_avatar") == "client" and p.get("status") in ("open", "in_progress")
    ]


def user_can_access_project(project: dict[str, Any], user: dict[str, Any] | None) -> bool:
    """Owned projects require matching user; unowned (demo/legacy) stay shared."""
    owner = project.get("owner_user_id")
    if not owner:
        return True
    if not user:
        return False
    if user.get("role") == "admin":
        return True
    if user.get("role") in ("qa_hunter", "both") and project.get("status") in (
        "open",
        "in_progress",
    ):
        return True
    return owner == user.get("id")


def find_project_for_suite(suite_name: str) -> dict[str, Any] | None:
    config_path = f"y/{suite_name}/{suite_name}.json"
    for p in load_projects():
        if p.get("suite_name") == suite_name or p.get("suite_config") == config_path:
            return p
    return None


def get_or_create_for_suite(suite_name: str, suite_detail: dict[str, Any] | None = None) -> dict[str, Any]:
    existing = find_project_for_suite(suite_name)
    if existing:
        return existing
    detail = suite_detail or {}
    config_path = detail.get("path") or f"y/{suite_name}/{suite_name}.json"
    return create_project(
        {
            "name": suite_name,
            "app_url": detail.get("url") or "",
            "purpose": detail.get("description") or "",
            "suite_name": suite_name,
            "suite_config": config_path,
        }
    )


def create_project(body: dict[str, Any]) -> dict[str, Any]:
    projects = load_projects()
    name = body.get("name", "").strip() or "Untitled project"
    purpose = body.get("purpose", body.get("prompt", "")).strip()
    suite_name = (body.get("suite_name") or "").strip()
    suite_config = (body.get("suite_config") or "").strip()
    app_url = body.get("app_url", "").strip()
    context_items = list(body.get("context_items") or [])
    if app_url and not any(c.get("kind") == "url" for c in context_items):
        context_items.insert(
            0,
            {
                "id": uuid.uuid4().hex[:8],
                "kind": "url",
                "label": "App URL",
                "value": app_url,
                "added_at": _now(),
            },
        )
    project = _normalize(
        {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "app_url": app_url,
            "suite_name": suite_name,
            "suite_config": suite_config,
            "purpose": purpose,
            "prompt": purpose,
            "owner_avatar": "client",
            "owner_user_id": body.get("owner_user_id"),
            "status": "open",
            "documents": [],
            "context_items": context_items,
            "chat_messages": [],
            "budget_usd": float(body.get("budget_usd") or 0),
            "budget_split": body.get("budget_split")
            or {"automation_pct": 50, "human_pct": 50},
            "hitl_consultants": [],
            "reports": [],
            "ai_enabled": body.get("ai_enabled", True),
            "brahl_context_path": body.get("brahl_context_path"),
            "brahl_plan_draft": body.get("brahl_plan_draft"),
            "latest_run": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
    )
    projects.append(project)
    save_projects(projects)
    return project


def update_project(project_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        allowed = {
            "name",
            "app_url",
            "purpose",
            "prompt",
            "status",
            "brahl_context_path",
            "latest_run",
            "budget_usd",
            "budget_split",
            "context_items",
            "chat_messages",
            "hitl_consultants",
            "ai_enabled",
            "cycle_history",
            "suite_name",
            "suite_config",
            "hitl_stories",
            "hitl_invites",
            "change_requests",
            "runtime_mode",
            "app_version",
            "baseline_version",
            "baseline_run",
            "owner_user_id",
            "ai_journey_notes",
            "ypad_summary",
            "current_phase",
            "brahl_decision",
        }
        for key, val in patch.items():
            if key in allowed:
                p[key] = val
        if "purpose" in patch:
            p["prompt"] = p.get("purpose") or ""
            # Living AI journey: note purpose changes in cycle trail
            hist = list(p.get("cycle_history") or [])
            hist.insert(
                0,
                {
                    "id": uuid.uuid4().hex[:8],
                    "step": "build",
                    "detail": "Purpose updated",
                    "at": _now(),
                },
            )
            p["cycle_history"] = hist[:50]
        p["updated_at"] = _now()
        p["ai_journey_updated_at"] = p["updated_at"]
        projects[i] = p
        save_projects(projects)
        return p
    raise KeyError(project_id)


def append_cycle_event(project_id: str, step: str, detail: str = "", run_name: str | None = None) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry: dict[str, Any] = {"id": uuid.uuid4().hex[:8], "step": step, "detail": detail, "at": _now()}
        if run_name:
            entry["run_name"] = run_name
            from runner import report_stats

            st = report_stats(run_name)
            entry["stats"] = {
                "passes": st.get("passes", 0),
                "fails": st.get("fails", 0),
                "total_plans": st.get("total_plans", 0),
                "health": st.get("health"),
            }
        history = list(p.get("cycle_history") or [])
        history.insert(0, entry)
        p["cycle_history"] = history[:50]
        p["current_phase"] = step
        p["updated_at"] = _now()
        p["ai_journey_updated_at"] = p["updated_at"]
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def add_chat_message(project_id: str, role: str, text: str) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {"id": uuid.uuid4().hex[:8], "role": role, "text": text.strip(), "at": _now()}
        msgs = list(p.get("chat_messages") or [])
        msgs.append(entry)
        p["chat_messages"] = msgs
        if role == "user" and text.strip():
            p["purpose"] = text.strip()
            p["prompt"] = text.strip()
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def apply_project_ai_usage(project_id: str, entry: dict[str, Any]) -> None:
    """Merge metered LLM usage into project.ai_usage."""
    if not project_id or not entry:
        return
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        u = dict(p.get("ai_usage") or {})
        u["calls"] = int(u.get("calls") or 0) + 1
        u["prompt_tokens"] = int(u.get("prompt_tokens") or 0) + int(entry.get("prompt_tokens") or 0)
        u["completion_tokens"] = int(u.get("completion_tokens") or 0) + int(entry.get("completion_tokens") or 0)
        u["total_tokens"] = int(u.get("total_tokens") or 0) + int(entry.get("total_tokens") or 0)
        u["usd_est"] = round(float(u.get("usd_est") or 0) + float(entry.get("usd_est") or 0), 6)
        u["updated_at"] = _now()
        p["ai_usage"] = u
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return


def assistant_reply(project: dict[str, Any], user_text: str) -> str:
    """Build assistant — OpenAI when AI on + key set, else scripted fallback."""
    if project.get("ai_enabled", True):
        try:
            import ai_assist

            ai_text = ai_assist.build_assistant_reply(
                project,
                user_text,
                on_usage=lambda entry: apply_project_ai_usage(project.get("id") or "", entry),
            )
            if ai_text:
                return ai_text
        except Exception:
            pass
    return _scripted_assistant_reply(project, user_text)


def _scripted_assistant_reply(project: dict[str, Any], user_text: str) -> str:
    msgs = [m for m in project.get("chat_messages", []) if m.get("role") == "user"]
    ctx_count = len(project.get("context_items") or [])
    budget = float(project.get("budget_usd") or 0)
    lower = user_text.lower().strip()

    if "[change request]" in lower or "change request:" in lower:
        detail = user_text.replace("[Change request]", "").replace("Change request:", "").strip()
        ctx = len(project.get("context_items") or [])
        return (
            f"Rebuild noted: {detail or 'project scope changed'}. "
            f"Next: review yPAD tabs (Plans/Actions/Designs), add QA Hunter user stories for new journeys, "
            f"{'update connectors if specs moved (+ below), ' if ctx else 'add connectors (+ below) for API docs or screenshots, '}"
            "then Run → Loop → Verify. Full reports on the BRAHL tab."
        )
    if "budget" in lower or lower.startswith("updated budget"):
        return (
            f"Budget ${budget:.0f} saved ({project['budget_split']['automation_pct']}% BRAHL automation / "
            f"{project['budget_split']['human_pct']}% QA Hunter). "
            "Invite QA Hunters when you need exploratory UX or edge-case coverage."
        )
    if len(msgs) <= 1:
        return (
            "What is the main purpose of this BRAHL cycle? "
            "Describe what we should validate, explore, or improve."
        )
    if len(msgs) == 2 and ctx_count == 0 and lower not in ("none", "no", "skip"):
        return (
            "Any connector or source of truth? (JIRA, Linear, Confluence, GitHub, specs, API docs). "
            "Tap + to add one — or reply 'none' to skip."
        )
    if budget <= 0:
        return (
            "Set your project budget below. We split funds between BRAHL automation "
            "(AI + FoXYiZ) and QA Hunters who enrich reports offline."
        )
    hitl = len(project.get("hitl_consultants") or [])
    if hitl == 0:
        return (
            f"Budget ${budget:.0f} noted ({project['budget_split']['automation_pct']}% automation / "
            f"{project['budget_split']['human_pct']}% QA Hunter). "
            "QA Hunters can join when you're ready. Use Loop to capture Step 0 context."
        )
    return (
        f"{hitl} QA Hunter(s) active. "
        "Keep adding context with + or proceed to Run / Loop."
    )


def add_context_item(project_id: str, kind: str, label: str, value: str) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {
            "id": uuid.uuid4().hex[:8],
            "kind": kind or "note",
            "label": label.strip() or kind,
            "value": value.strip(),
            "added_at": _now(),
        }
        items = list(p.get("context_items") or [])
        items.append(entry)
        p["context_items"] = items
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def add_document(project_id: str, filename: str, content: bytes) -> dict[str, Any]:
    _ensure_dirs()
    safe_name = Path(filename).name
    project_dir = UPLOADS_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    dest = project_dir / safe_name
    dest.write_bytes(content)
    rel = dest.relative_to(DATA_DIR.parent).as_posix()
    doc = {"name": safe_name, "path": rel}
    add_context_item(project_id, "document", safe_name, rel)
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        docs = list(p.get("documents") or [])
        docs = [d for d in docs if d.get("name") != safe_name]
        docs.append(doc)
        p["documents"] = docs
        projects[i] = p
        save_projects(projects)
        return doc
    raise KeyError(project_id)


EVIDENCE_KINDS = (
    "screen_recording",
    "audio_note",
    "screenshot",
    "video",
    "file",
    "document",
    "url",
    "note",
)


def add_evidence_item(
    project_id: str,
    kind: str,
    *,
    author: str = "",
    url: str = "",
    path: str = "",
    title: str = "",
    note: str = "",
    finding_id: str | None = None,
    report_id: str | None = None,
) -> dict[str, Any]:
    """Add one normalized evidence item to the project's searchable library."""
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        items = list(p.get("evidence_library") or [])
        norm_kind = (kind or "note").strip().lower()
        if norm_kind not in EVIDENCE_KINDS:
            norm_kind = "note"
        entry = {
            "id": uuid.uuid4().hex[:10],
            "kind": norm_kind,
            "author": (author or "").strip() or "unknown",
            "created_at": _now(),
            "finding_id": (finding_id or None),
            "report_id": (report_id or None),
            "url": (url or "").strip(),
            "path": (path or "").strip(),
            "title": (title or "").strip(),
            "note": (note or "").strip(),
        }
        items.append(entry)
        p["evidence_library"] = items
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def list_evidence(
    project_id: str,
    *,
    kind: str | None = None,
    query: str | None = None,
    report_id: str | None = None,
    finding_id: str | None = None,
) -> list[dict[str, Any]]:
    """Searchable evidence index — the single library backing BRAHL/Hunter UI.

    Merges the normalized evidence_library with legacy context_items/documents
    (links + uploads added before this feature) so the project library stays
    the one searchable index without losing older entries.
    """
    project = get_project(project_id)
    if not project:
        raise KeyError(project_id)
    items = list(project.get("evidence_library") or [])
    known_paths = {(i.get("path") or i.get("url") or "").strip() for i in items if (i.get("path") or i.get("url"))}
    for c in project.get("context_items") or []:
        value = (c.get("value") or "").strip()
        if not value or value in known_paths:
            continue
        is_url = value.lower().startswith(("http://", "https://"))
        items.append(
            {
                "id": f"ctx-{c.get('id') or value[:8]}",
                "kind": "url" if is_url else "document" if c.get("kind") == "document" else "note",
                "author": "",
                "created_at": c.get("added_at") or "",
                "finding_id": None,
                "report_id": None,
                "url": value if is_url else "",
                "path": "" if is_url else value,
                "title": c.get("label") or value,
                "note": "" if c.get("kind") != "note" else value,
                "legacy": True,
            }
        )
        known_paths.add(value)
    for d in project.get("documents") or []:
        value = (d.get("path") or "").strip()
        if not value or value in known_paths:
            continue
        items.append(
            {
                "id": f"doc-{value[-12:]}",
                "kind": "document",
                "author": "",
                "created_at": "",
                "finding_id": None,
                "report_id": None,
                "url": "",
                "path": value,
                "title": d.get("name") or value,
                "note": "",
                "legacy": True,
            }
        )
        known_paths.add(value)
    if kind:
        items = [i for i in items if i.get("kind") == kind]
    if report_id:
        items = [i for i in items if i.get("report_id") == report_id]
    if finding_id:
        items = [i for i in items if i.get("finding_id") == finding_id]
    if query and query.strip():
        q = query.strip().lower()
        items = [
            i
            for i in items
            if q in (i.get("title") or "").lower()
            or q in (i.get("note") or "").lower()
            or q in (i.get("url") or "").lower()
            or q in (i.get("path") or "").lower()
            or q in (i.get("kind") or "").lower()
            or q in (i.get("author") or "").lower()
        ]
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items


def link_evidence(
    project_id: str,
    evidence_ids: list[str],
    *,
    report_id: str | None = None,
    finding_id: str | None = None,
) -> list[dict[str, Any]]:
    """Attach existing library evidence to a report and/or a finding."""
    if not evidence_ids:
        return []
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        items = list(p.get("evidence_library") or [])
        wanted = {str(x).strip() for x in evidence_ids if str(x).strip()}
        updated: list[dict[str, Any]] = []
        for item in items:
            if item.get("id") in wanted:
                if report_id:
                    item["report_id"] = report_id
                if finding_id:
                    item["finding_id"] = finding_id
                updated.append(item)
        p["evidence_library"] = items
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return updated
    raise KeyError(project_id)


def add_hitl_story(project_id: str, title: str, description: str = "") -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        story = {
            "id": uuid.uuid4().hex[:8],
            "title": title.strip(),
            "description": description.strip(),
            "status": "open",
            "created_at": _now(),
        }
        stories = list(p.get("hitl_stories") or [])
        stories.append(story)
        p["hitl_stories"] = stories
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return story
    raise KeyError(project_id)


def invite_hitl(
    project_id: str,
    note: str = "",
    consultant_name: str = "",
    email: str = "",
    bug_bounty: bool = False,
    consultant_tag: str = "",
) -> dict[str, Any]:
    """Client invites Human in the Loop (individual or team) to join this project."""
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        invites = list(p.get("hitl_invites") or [])
        invite = {
            "id": uuid.uuid4().hex[:8],
            "note": note.strip(),
            "consultant_name": consultant_name.strip(),
            "team_name": consultant_name.strip(),  # legacy display
            "consultant_tag": consultant_tag.strip(),
            "email": email.strip(),
            "bug_bounty": bool(bug_bounty),
            "status": "pending",
            "invited_at": _now(),
        }
        invites.append(invite)
        p["hitl_invites"] = invites
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return invite
    raise KeyError(project_id)


def request_change_assistance(project_id: str, note: str = "") -> dict[str, Any]:
    """Client signals the app changed and needs a new BRAHL cycle."""
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {
            "id": uuid.uuid4().hex[:8],
            "note": note.strip() or "Project has changed — need assistance again.",
            "status": "open",
            "requested_at": _now(),
        }
        history = list(p.get("change_requests") or [])
        history.insert(0, entry)
        p["change_requests"] = history[:20]
        p["status"] = "in_progress"
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def snapshot_version_baseline(
    project_id: str,
    version_label: str = "",
    run_name: str | None = None,
) -> dict[str, Any]:
    """Pin the latest (or chosen) verify run as the old-version baseline before a launch upgrade."""
    from runner import analyze_run

    project = get_project(project_id)
    if not project:
        raise KeyError(project_id)
    run = (run_name or project.get("latest_run") or "").strip()
    if not run:
        raise ValueError("No verify run to snapshot — run Loop → Verify on the old app first.")
    stats = analyze_run(run)
    if not stats.get("has_results"):
        raise ValueError(f"No zResults for run `{run}` — complete Verify before saving baseline.")
    label = version_label.strip() or (project.get("app_version") or "").strip() or "baseline"
    return update_project(
        project_id,
        {
            "baseline_run": run,
            "baseline_version": label,
        },
    )


def join_hitl(project_id: str, consultant_name: str = "Consultant") -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        team = list(p.get("hitl_consultants") or [])
        if any(c.get("id") == HITL_CONSULTANT_ID for c in team):
            return p
        for inv in p.get("hitl_invites") or []:
            if inv.get("status") == "pending":
                inv["status"] = "accepted"
        team.append(
            {
                "id": HITL_CONSULTANT_ID,
                "name": consultant_name,
                "joined_at": _now(),
                "deliverables": {
                    "critical_issues": 0,
                    "time_hours": 0.0,
                    "features_found": 0,
                    "reports_submitted": 0,
                },
            }
        )
        p["hitl_consultants"] = team
        p["status"] = "in_progress"
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return p
    raise KeyError(project_id)


def _resolve_upload_path(project_id: str, report_path: str) -> Path | None:
    """Resolve a project upload path (data/uploads/...) to an absolute file."""
    if not report_path:
        return None
    norm = report_path.replace("\\", "/")
    if norm.startswith("data/uploads/"):
        path = DATA_DIR.parent / norm
    elif norm.startswith("qoa_web/data/uploads/"):
        path = KK_ROOT / norm
    else:
        name = Path(norm).name
        path = UPLOADS_DIR / project_id / name
    return path if path.is_file() else None


def load_project_report_markdown(project_id: str, report: dict[str, Any]) -> str:
    """Load markdown from z/ run output or project upload."""
    report_path = (report.get("report_path") or "").strip()
    run_name = report.get("run_name", "")
    if report_path:
        upload = _resolve_upload_path(project_id, report_path)
        if upload:
            return upload.read_text(encoding="utf-8", errors="replace")
    path = _resolve_report_file(run_name)
    if path:
        return path.read_text(encoding="utf-8", errors="replace")
    raise FileNotFoundError(run_name)


def submit_hitl_report(
    project_id: str,
    run_name: str,
    report_path: str | None = None,
    *,
    critical_issues: int = 0,
    time_hours: float = 0.0,
    features_found: int = 0,
    hunt_report_path: str | None = None,
    artifact_paths: list[str] | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        reports = list(p.get("reports") or [])
        report_source = (
            "automation_ai"
            if p.get("ai_enabled") is False
            else "human_in_the_loop"
        )
        resolved_path = hunt_report_path or report_path
        entry = {
            "id": uuid.uuid4().hex[:8],
            "run_name": run_name,
            "report_path": resolved_path,
            "submitted_at": _now(),
            "source": report_source,
            "artifacts": list(artifact_paths or []),
            "evidence_ids": list(evidence_ids or []),
            "archived": False,
        }
        reports.append(entry)
        p["reports"] = reports
        p["latest_run"] = run_name
        team = list(p.get("hitl_consultants") or [])
        for c in team:
            if c.get("id") == HITL_CONSULTANT_ID:
                d = dict(c.get("deliverables") or {})
                d["critical_issues"] = d.get("critical_issues", 0) + critical_issues
                d["time_hours"] = float(d.get("time_hours", 0)) + time_hours
                d["features_found"] = d.get("features_found", 0) + features_found
                d["reports_submitted"] = d.get("reports_submitted", 0) + 1
                c["deliverables"] = d
        p["hitl_consultants"] = team
        if evidence_ids:
            wanted = {str(x).strip() for x in evidence_ids if str(x).strip()}
            lib = list(p.get("evidence_library") or [])
            for item in lib:
                if item.get("id") in wanted:
                    item["report_id"] = entry["id"]
            p["evidence_library"] = lib
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def compute_payout_preview(project: dict[str, Any]) -> list[dict[str, Any]]:
    """Simple payout split preview by deliverable weight."""
    budget = float(project.get("budget_usd") or 0)
    human_pool = budget * (project.get("budget_split") or {}).get("human_pct", 50) / 100
    team = project.get("hitl_consultants") or []
    if not team or human_pool <= 0:
        return []
    weights = []
    for c in team:
        d = c.get("deliverables") or {}
        w = (
            d.get("critical_issues", 0) * 3
            + d.get("features_found", 0) * 2
            + float(d.get("time_hours", 0))
            + d.get("reports_submitted", 0) * 5
        )
        weights.append(max(w, 0.1 if c else 0))
    total = sum(weights) or 1
    out = []
    for c, w in zip(team, weights):
        out.append(
            {
                "consultant_id": c.get("id"),
                "name": c.get("name"),
                "weight": w,
                "payout_usd": round(human_pool * w / total, 2),
                "deliverables": c.get("deliverables"),
            }
        )
    return out


def compute_cost_meter(project: dict[str, Any], runtime_mode: str | None = None) -> dict[str, Any]:
    """Estimate budget use by BRAHL phase — local FoXYiZ vs cloud runtime."""
    budget = float(project.get("budget_usd") or 0)
    split = project.get("budget_split") or {"automation_pct": 50, "human_pct": 50}
    auto_pct = int(split.get("automation_pct", 50))
    human_pct = int(split.get("human_pct", 50))
    auto_pool = round(budget * auto_pct / 100, 2)
    human_pool = round(budget * human_pct / 100, 2)
    mode = (runtime_mode or project.get("runtime_mode") or "local").lower()
    if mode not in ("local", "cloud"):
        mode = "local"

    chat_n = len(project.get("chat_messages") or [])
    user_msgs = len([m for m in project.get("chat_messages") or [] if m.get("role") == "user"])
    cycle_n = len(project.get("cycle_history") or [])
    loop_cycles = min(3, max(1, (cycle_n + 1) // 2)) if cycle_n else 0
    has_run = bool(project.get("latest_run"))
    ai_on = project.get("ai_enabled", True)
    change_n = len(project.get("change_requests") or [])
    hitl_n = len(project.get("hitl_consultants") or [])
    a77 = project.get("atomic77_usage") or {}
    a77_user = int(a77.get("user_messages") or 0)
    a77_tokens = int(a77.get("tokens_est") or 0)
    ai_u = project.get("ai_usage") or {}
    ai_tokens = int(ai_u.get("total_tokens") or 0)
    ai_usd = float(ai_u.get("usd_est") or 0)

    build_activity = min(1.0, (user_msgs + change_n * 2) / 8.0) if ai_on else 0.2
    atomic77_activity = min(1.0, a77_user / 6.0) if a77_user else 0.0
    if not ai_on and a77_user:
        atomic77_activity = min(0.5, a77_user / 10.0)
    analyze_activity = 0.35 if has_run and ai_on else 0.0
    heal_activity = 0.25 if has_run and ai_on else 0.0

    if mode == "local":
        phase_template = [
            ("build", "Build", 0.38, "ai", f"AI chat · yPAD · ~{ai_tokens} tok / ${ai_usd:.3f}"),
            ("atomic77", "Atomic 77", 0.08, "ai", f"Idea-to-launch assistant · ~{a77_tokens} tokens est."),
            ("run", "Run", 0.0, "local", "FoXYiZ on your desktop — no cloud charge"),
            ("analyze", "Analyze", 0.18, "ai", "AI root-cause when enabled"),
            ("heal", "Heal", 0.15, "ai", "AI heal suggestions when enabled"),
            ("loop", "Loop", 0.05, "local", "FoXYiZ cycles locally · shrink/restore"),
            ("brahl", "BRAHL", 0.0, "local", "Reports from z/ — view & share"),
        ]
        run_activity = 0.15 if has_run else 0.0
        loop_activity = min(1.0, loop_cycles / 3.0) if loop_cycles else 0.0
    else:
        phase_template = [
            ("build", "Build", 0.20, "ai", "AI chat · yPAD scope"),
            ("atomic77", "Atomic 77", 0.06, "ai", f"Idea-to-launch · ~{a77_tokens} tokens est."),
            ("run", "Run", 0.28, "cloud", "Cloud browser / engine minutes"),
            ("analyze", "Analyze", 0.16, "ai", "AI analyze on z/ results"),
            ("heal", "Heal", 0.14, "ai", "AI heal on failures"),
            ("loop", "Loop", 0.15, "cloud", f"Automated re-runs · up to {max(loop_cycles, 1)}× on failures"),
            ("brahl", "BRAHL", 0.05, "cloud", "Report storage & delivery"),
        ]
        run_activity = 0.4 if has_run else 0.0
        loop_activity = min(1.0, loop_cycles / 3.0) if loop_cycles else 0.0

    activity_map = {
        "build": build_activity,
        "atomic77": atomic77_activity,
        "run": run_activity,
        "analyze": analyze_activity,
        "heal": heal_activity,
        "loop": loop_activity,
        "brahl": 0.2 if project.get("reports") else 0.0,
    }

    phases: list[dict[str, Any]] = []
    spent_auto = 0.0
    for key, label, alloc_pct, cost_type, note in phase_template:
        allocated = round(auto_pool * alloc_pct, 2)
        act = activity_map.get(key, 0.0)
        spent = round(allocated * act, 2) if allocated > 0 else 0.0
        spent_auto += spent
        phases.append(
            {
                "phase": key,
                "label": label,
                "allocated_usd": allocated,
                "spent_usd": spent,
                "cost_type": cost_type,
                "note": note,
                "activity_pct": round(act * 100),
            }
        )

    payout = compute_payout_preview(project)
    spent_human = round(sum(p.get("payout_usd", 0) for p in payout), 2) if payout else 0.0
    if hitl_n and human_pool > 0 and not spent_human:
        spent_human = round(human_pool * 0.15, 2)

    total_spent = round(spent_auto + spent_human, 2)
    remaining = round(max(0, budget - total_spent), 2)

    from pricing import CREATOR_WALLET_MIN_USD, PLATFORM_FEE_PCT, get_pricing_rules

    deposit_split = get_pricing_rules(budget, auto_pct, human_pct)["project_deposit_split"]

    return {
        "budget_usd": budget,
        "budget_min_usd": CREATOR_WALLET_MIN_USD,
        "platform_fee_pct": PLATFORM_FEE_PCT,
        "deposit_split": deposit_split,
        "automation_pool_usd": auto_pool,
        "human_pool_usd": human_pool,
        "automation_pct": auto_pct,
        "human_pct": human_pct,
        "runtime_mode": mode,
        "spent_automation_usd": round(spent_auto, 2),
        "spent_human_usd": spent_human,
        "spent_total_usd": total_spent,
        "remaining_usd": remaining,
        "budget_used_pct": round(100 * total_spent / budget, 1) if budget > 0 else 0,
        "phases": phases,
        "loop_cycles_est": loop_cycles,
        "ai_enabled": ai_on,
        "philosophy": (
            "Fund your QA wallet from $50+. QAonAIR retains 5%; the rest flows to AI, QA Hunter payouts, "
            "and ops — minimize cloud spend, maximize local FoXYiZ + human craft."
        ),
        "hitl_payouts": payout,
        "atomic77_usage": {
            "messages": int(a77.get("messages") or 0),
            "tokens_est": a77_tokens,
            "user_messages": a77_user,
        },
        "ai_usage": {
            "calls": int(ai_u.get("calls") or 0),
            "total_tokens": ai_tokens,
            "usd_est": ai_usd,
        },
    }


def consultant_wallet(consultant_id: str = HITL_CONSULTANT_ID) -> dict[str, Any]:
    """HITL earnings view across joined client projects."""
    projects = load_projects()
    rows: list[dict[str, Any]] = []
    total = 0.0
    for p in projects:
        if p.get("owner_avatar") != "client":
            continue
        team = p.get("hitl_consultants") or []
        member = next((c for c in team if c.get("id") == consultant_id), None)
        if not member:
            continue
        payouts = compute_payout_preview(p)
        mine = next((x for x in payouts if x.get("consultant_id") == consultant_id), None)
        earned = float(mine.get("payout_usd", 0)) if mine else 0.0
        total += earned
        rows.append(
            {
                "project_id": p.get("id"),
                "project_name": p.get("name"),
                "suite_name": p.get("suite_name"),
                "budget_usd": float(p.get("budget_usd") or 0),
                "human_pool_usd": round(
                    float(p.get("budget_usd") or 0)
                    * (p.get("budget_split") or {}).get("human_pct", 50)
                    / 100,
                    2,
                ),
                "earned_usd": earned,
                "deliverables": member.get("deliverables") or {},
                "status": p.get("status"),
            }
        )
    return {
        "consultant_id": consultant_id,
        "total_earned_usd": round(total, 2),
        "projects": rows,
        "philosophy": (
            "Earn by QA Hunting or Promoting — any avatar can load their wallet. "
            "Payout at $100+ or spend credits to QA-hunt your own creations."
        ),
    }


def _resolve_report_file(run_name: str) -> Path | None:
    in_run = Z_DIR / run_name / "brahl_report.md"
    if in_run.is_file():
        return in_run
    flat = Z_DIR / f"brahl_report_{run_name}.md"
    if flat.is_file():
        return flat
    return None


def register_brahl_report(
    project_id: str,
    run_name: str,
    source: str = "automation",
    report_path: str | None = None,
    *,
    batch_id: str | None = None,
    batch_dashboard: str | None = None,
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        project_suite = (p.get("suite_name") or "").strip()
        parts = run_name.split("_")
        run_suite = "_".join(parts[2:]) if len(parts) >= 3 else ""
        if project_suite and run_suite and run_suite != project_suite:
            try:
                from runner import _y_suite_names

                known = set(_y_suite_names())
            except Exception:
                known = set()
            if run_suite in known:
                raise ValueError(
                    f"Run '{run_name}' belongs to suite '{run_suite}', "
                    f"not project suite '{project_suite}'"
                )
        reports = list(p.get("reports") or [])
        for r in reports:
            if r.get("run_name") == run_name:
                return r
        resolved = _resolve_report_file(run_name)
        if not resolved:
            try:
                from runner import default_fstart_for_suite, ensure_brahl_report

                suite = run_name.split("_")
                suite_name = "_".join(suite[2:]) if len(suite) >= 3 else ""
                ensure_brahl_report(
                    run_name,
                    config_path=default_fstart_for_suite(suite_name or project_suite)
                    if (suite_name or project_suite)
                    else "f/fStart/Math.json",
                    project=p,
                )
                resolved = _resolve_report_file(run_name)
            except FileNotFoundError:
                resolved = None
        path = report_path or (
            f"z/{run_name}/brahl_report.md" if resolved else None
        )
        entry = {
            "id": uuid.uuid4().hex[:8],
            "run_name": run_name,
            "report_path": path,
            "submitted_at": _now(),
            "source": source if source in REPORT_SOURCE_LABELS else "automation",
            "batch_id": (batch_id or None),
            "batch_dashboard": (batch_dashboard or None),
            "archived": False,
        }
        reports.append(entry)
        p["reports"] = reports
        p["latest_run"] = run_name
        if evidence_ids:
            wanted = {str(x).strip() for x in evidence_ids if str(x).strip()}
            lib = list(p.get("evidence_library") or [])
            for item in lib:
                if item.get("id") in wanted:
                    item["report_id"] = entry["id"]
            p["evidence_library"] = lib
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def register_brahl_report_batch(
    project_id: str,
    run_names: list[str],
    source: str = "automation",
    *,
    batch_dashboard: str | None = None,
    job_id: str | None = None,
) -> dict[str, Any]:
    """Register every child run_dir of a parallel batch as its own report, grouped by batch_id."""
    clean = [r.strip() for r in (run_names or []) if (r or "").strip()]
    if not clean:
        return {"entries": [], "batch_id": None}
    batch_id = job_id or uuid.uuid4().hex[:10]
    entries: list[dict[str, Any]] = []
    for run_name in clean:
        try:
            entry = register_brahl_report(
                project_id,
                run_name,
                source,
                batch_id=batch_id,
                batch_dashboard=batch_dashboard,
            )
        except ValueError:
            continue
        entries.append(entry)
    return {"entries": entries, "batch_id": batch_id, "batch_dashboard": batch_dashboard}


def list_brahl_reports(project_id: str) -> list[dict[str, Any]]:
    project = get_project(project_id)
    if not project:
        raise KeyError(project_id)
    project = _normalize(project)
    reports = list(project.get("reports") or [])
    run_names = {r.get("run_name") for r in reports}
    latest = project.get("latest_run")
    if latest and latest not in run_names and _resolve_report_file(latest):
        register_brahl_report(project_id, latest, source="automation")
        project = get_project(project_id)
        reports = list((project or {}).get("reports") or [])

    enriched: list[dict[str, Any]] = []
    for r in reports:
        run_name = r.get("run_name", "")
        src = r.get("source") or "automation"
        path = _resolve_report_file(run_name)
        upload_path = None
        rp = (r.get("report_path") or "").strip()
        if rp:
            upload_path = _resolve_upload_path(project_id, rp)
        enriched.append(
            {
                **r,
                "source": src,
                "source_label": REPORT_SOURCE_LABELS.get(src, src),
                "has_file": path is not None or upload_path is not None,
                "is_hunt_report": bool(upload_path and "hunt-report" in Path(rp).name),
                "archived": bool(r.get("archived", False)),
            }
        )
    enriched.sort(key=lambda x: x.get("submitted_at") or "", reverse=True)
    return enriched


def set_report_archived(project_id: str, report_id: str, archived: bool) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        reports = list(p.get("reports") or [])
        found = None
        for r in reports:
            if r.get("id") == report_id:
                r["archived"] = bool(archived)
                found = r
        if found is None:
            raise KeyError(report_id)
        p["reports"] = reports
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return found
    raise KeyError(project_id)


def load_report_markdown(run_name: str, project: dict[str, Any] | None = None) -> str:
    path = _resolve_report_file(run_name)
    if not path:
        from runner import ensure_brahl_report

        path = ensure_brahl_report(run_name, project=project)
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_section(md: str, heading: str) -> str:
    for marker in (f"## {heading}", f"### {heading}"):
        if marker not in md:
            continue
        part = md.split(marker, 1)[1]
        nxt = part.find("\n## ")
        return (part[:nxt] if nxt >= 0 else part).strip()[:1200]
    return ""


def _report_headline(report_md: str) -> str:
    for heading in (
        "Executive summary (for customer / product owner)",
        "Executive summary",
        "Summary",
    ):
        section = _extract_section(report_md, heading)
        if section:
            return section
    return report_md[:800]


def add_brahl_chat_message(project_id: str, role: str, text: str) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {"id": uuid.uuid4().hex[:8], "role": role, "text": text.strip(), "at": _now()}
        msgs = list(p.get("brahl_chat_messages") or [])
        msgs.append(entry)
        p["brahl_chat_messages"] = msgs
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def add_team_message(
    project_id: str,
    text: str,
    *,
    author: str = "You",
    author_role: str = "creator",
) -> dict[str, Any]:
    """Human team thread (Creator + QA Hunters) — not AI Build/BRAHL chat."""
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {
            "id": uuid.uuid4().hex[:8],
            "author": (author or "You").strip() or "You",
            "author_role": author_role if author_role in ("creator", "hunter", "system") else "creator",
            "text": text.strip(),
            "at": _now(),
        }
        msgs = list(p.get("team_messages") or [])
        msgs.append(entry)
        # Keep last 200 messages
        p["team_messages"] = msgs[-200:]
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def add_team_task(
    project_id: str,
    title: str,
    *,
    assignee: str = "",
    created_by: str = "Creator",
) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {
            "id": uuid.uuid4().hex[:8],
            "title": title.strip(),
            "assignee": (assignee or "").strip(),
            "status": "open",
            "created_by": (created_by or "Creator").strip() or "Creator",
            "at": _now(),
        }
        tasks = list(p.get("team_tasks") or [])
        tasks.append(entry)
        p["team_tasks"] = tasks
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def update_team_task(project_id: str, task_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        tasks = list(p.get("team_tasks") or [])
        found = None
        for t in tasks:
            if t.get("id") == task_id:
                if "status" in patch and patch["status"] in ("open", "done"):
                    t["status"] = patch["status"]
                if "assignee" in patch:
                    t["assignee"] = str(patch.get("assignee") or "").strip()
                if "title" in patch and str(patch.get("title") or "").strip():
                    t["title"] = str(patch["title"]).strip()
                t["updated_at"] = _now()
                found = t
                break
        if not found:
            raise KeyError(task_id)
        p["team_tasks"] = tasks
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return found
    raise KeyError(project_id)


def add_atomic77_chat_message(project_id: str, role: str, text: str) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        entry = {"id": uuid.uuid4().hex[:8], "role": role, "text": text.strip(), "at": _now()}
        msgs = list(p.get("atomic77_chat_messages") or [])
        msgs.append(entry)
        p["atomic77_chat_messages"] = msgs
        usage = dict(p.get("atomic77_usage") or {})
        usage["messages"] = len(msgs)
        if role == "user":
            usage["user_messages"] = int(usage.get("user_messages") or 0) + 1
        p["atomic77_usage"] = usage
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


def record_atomic77_tokens(project_id: str, tokens_est: int) -> None:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        usage = dict(p.get("atomic77_usage") or {})
        usage["tokens_est"] = int(usage.get("tokens_est") or 0) + max(0, tokens_est)
        p["atomic77_usage"] = usage
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return
    raise KeyError(project_id)


def brahl_model_reply(
    project: dict[str, Any],
    report_md: str | None,
    user_text: str,
    run_name: str | None = None,
) -> str:
    """Answer from BRAHL report (+ optional LLM when OPENAI_API_KEY is set)."""
    name = project.get("name") or "this project"
    purpose = project.get("purpose") or project.get("prompt") or "No purpose captured yet."
    lower = user_text.lower().strip()
    reports = project.get("reports") or []

    if not report_md:
        return (
            f"No verify results yet for **{name}**. "
            f"Run Loop → Verify, then open this tab — the report is built from zResults automatically. "
            f"Project purpose: {purpose[:200]}"
        )

    # Prefer grounded LLM over keyword shortcuts when available
    try:
        from ai_assist import chat_metered, is_ai_available, brahl_doc_context

        if is_ai_available() and (user_text or "").strip():
            stats_hint = ""
            try:
                from runner import report_stats

                rn = run_name or project.get("latest_run") or ""
                if rn:
                    st = report_stats(rn)
                    stats_hint = (
                        f"\nRun stats: {st.get('passes')}/{st.get('total_plans')} pass, "
                        f"{st.get('fails')} fail, health {st.get('health')}, "
                        f"~{st.get('duration_sec')}s.\n"
                    )
            except Exception:
                pass
            system = (
                "You are the BRAHL report assistant for QAonAir. "
                "Answer ONLY from the report markdown and stats below. "
                "Be concise (≤120 words). Use spelling BRAHL (never brawl). "
                "If the report lacks the answer, say so and suggest Verify or Heal next steps.\n\n"
                + brahl_doc_context(role="brahl_chat", project=project)
            )
            user = (
                f"Project: {name}\nPurpose: {purpose[:400]}\n"
                f"{stats_hint}\n"
                f"--- BRAHL report (truncated) ---\n{(report_md or '')[:6000]}\n---\n"
                f"User question: {user_text}"
            )
            reply, meta = chat_metered(
                system,
                user,
                project_id=project.get("id"),
                project=project,
                user_id=project.get("owner_user_id"),
                role="brahl_chat",
            )
            if meta.get("denied"):
                return meta.get("reason") or "AI quota exceeded."
            if reply:
                return reply.strip()
    except Exception:
        pass

    summary = _report_headline(report_md)

    if any(w in lower for w in ("how long", "duration", "time", "took")):
        from runner import report_stats

        run_name = run_name or project.get("latest_run") or ""
        if not run_name:
            for r in reports:
                if r.get("run_name"):
                    run_name = r["run_name"]
                    break
        if run_name:
            st = report_stats(run_name)
            return (
                f"**{name}** — run `{run_name}`: **{st['passes']}/{st['total_plans']} pass**, "
                f"engine time ~**{st['duration_sec']}s**, health **{st['health']}**."
            )

    if any(w in lower for w in ("summary", "executive", "overview", "health")):
        return f"**{name}** — from the BRAHL report:\n\n{summary}"

    if any(w in lower for w in ("fail", "issue", "defect", "bug", "fix")):
        section = _extract_section(report_md, "Failures (detail)") or _extract_section(
            report_md, "Customer action plan — next BRAHL run"
        )
        if section:
            return f"**{name}** — issues / action items:\n\n{section}"
        return f"**{name}** — no failures section. Summary:\n\n{summary[:500]}"

    if any(w in lower for w in ("loop", "cycle", "verify", "test", "ran", "run")):
        section = _extract_section(report_md, "Cycle summary") or _extract_section(
            report_md, "Loop detail — Verify"
        )
        if section:
            return f"**{name}** — cycle / verify:\n\n{section}"
        return f"**{name}** — latest verify:\n\n{summary[:500]}"

    if any(w in lower for w in ("human", "hitl", "consultant")):
        hitl = len(project.get("hitl_consultants") or [])
        human_reports = [r for r in reports if "human" in (r.get("source") or "")]
        return (
            f"**{name}** has {hitl} QA Hunter(s) and "
            f"{len(human_reports)} QA Hunter-enriched report(s). "
            "QA Hunter reports add critical issues and UX findings on top of automation."
        )

    if any(w in lower for w in ("purpose", "scope", "project", "origin", "prompt")):
        return f"**{name}** purpose / origin: {purpose}\n\nReport headline:\n{summary[:400]}"

    return (
        f"**{name}** — answers come from the BRAHL report above. "
        f"Try: summary, failures, how long, loop, health, origin.\n\n{summary[:350]}"
    )


def ecosystem_stats() -> dict[str, Any]:
    """Aggregate client / HITL / admin signals for the About page."""
    projects = load_projects()
    clients = [p for p in projects if p.get("owner_avatar") == "client"]

    chat_messages = 0
    change_requests = 0
    atomic77_messages = 0
    atomic77_tokens = 0
    hitl_stories = 0
    hitl_invites = 0
    hitl_invites_pending = 0
    consultants_joined = 0
    budget_total = 0.0
    projects_with_verify = 0
    cycle_events = 0
    active_building = 0

    for p in clients:
        chat_messages += len(p.get("chat_messages") or [])
        change_requests += len(p.get("change_requests") or [])
        a77u = p.get("atomic77_usage") or {}
        atomic77_messages += int(a77u.get("messages") or 0)
        atomic77_tokens += int(a77u.get("tokens_est") or 0)
        hitl_stories += len(p.get("hitl_stories") or [])
        for inv in p.get("hitl_invites") or []:
            hitl_invites += 1
            if inv.get("status") == "pending":
                hitl_invites_pending += 1
        consultants_joined += len(p.get("hitl_consultants") or [])
        budget_total += float(p.get("budget_usd") or 0)
        cycle_events += len(p.get("cycle_history") or [])
        if p.get("latest_run"):
            projects_with_verify += 1
        if p.get("status") in ("open", "in_progress") and (
            p.get("chat_messages") or p.get("change_requests") or p.get("latest_run")
        ):
            active_building += 1

    # Modest scores — activity-weighted, capped below 96 so we stay honest
    client_score = min(
        96,
        72
        + min(projects_with_verify * 4, 12)
        + min(chat_messages // 8, 8)
        + min(change_requests * 2, 6),
    )
    consultant_score = min(
        96,
        68
        + min(consultants_joined * 6, 18)
        + min((hitl_invites - hitl_invites_pending) * 3, 9)
        + min(hitl_stories // 2, 6),
    )

    return {
        "clients": {
            "count": len(clients),
            "active_building": active_building,
            "chat_messages": chat_messages,
            "change_requests": change_requests,
            "projects_with_verify": projects_with_verify,
            "hitl_stories": hitl_stories,
            "budget_usd": round(budget_total, 2),
        },
        "consultants": {
            "joined": consultants_joined,
            "invites_sent": hitl_invites,
            "invites_pending": hitl_invites_pending,
            "stories_to_cover": hitl_stories,
        },
        "brahl": {
            "cycle_events": cycle_events,
            "verified_projects": projects_with_verify,
        },
        "atomic77": {
            "messages": atomic77_messages,
            "tokens_est": atomic77_tokens,
        },
        "satisfaction": {
            "client_score": client_score,
            "consultant_score": consultant_score,
            "headline": "Keep clients and consultants modestly happy — and very satisfied.",
        },
    }


def apply_brahl_plan(
    project_id: str,
    plan: dict[str, Any],
    *,
    write_ypad: bool = True,
    created_by: str = "",
) -> dict[str, Any]:
    """Persist accepted BRAHL Plan — purpose, stories, draft; optionally rewrite yPAD CSVs."""
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        summary = (plan.get("summary") or "").strip()
        if summary:
            p["purpose"] = summary
            p["prompt"] = summary
        stories = list(p.get("hitl_stories") or [])
        existing_titles = {(s.get("title") or "").strip().lower() for s in stories}
        for story in plan.get("user_stories") or []:
            title = (story.get("title") or "").strip()
            if not title or title.lower() in existing_titles:
                continue
            desc = story.get("description") or ""
            if story.get("automated") is False:
                desc = (desc + " [manual — QA Hunter]").strip()
            stories.append(
                {
                    "id": uuid.uuid4().hex[:8],
                    "title": title,
                    "description": desc.strip(),
                    "status": "open",
                    "created_at": _now(),
                }
            )
            existing_titles.add(title.lower())
        p["hitl_stories"] = stories
        p["brahl_plan_draft"] = plan
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)

        if write_ypad:
            suite = (p.get("suite_name") or "").strip()
            if suite:
                try:
                    from runner import materialize_brahl_plan_for_suite

                    materialize_brahl_plan_for_suite(
                        suite,
                        app_url=p.get("app_url") or "",
                        brahl_plan=plan,
                        created_by=created_by,
                    )
                except Exception:
                    pass
                try:
                    import suite_docs as suite_docs_store

                    suite_docs_store.write_suite_docs_from_context(
                        suite, project=p, brahl_plan=plan
                    )
                except Exception:
                    pass
            # Capture / refresh Step 0 origin when purpose known
            try:
                from runner import capture_brahl_context, default_fstart_for_suite

                prompt = (p.get("purpose") or p.get("prompt") or summary or "").strip()
                if prompt:
                    fstart = default_fstart_for_suite(suite) if suite else "f/fStart/Math.json"
                    ctx = capture_brahl_context(prompt, fstart)
                    return update_project(
                        project_id,
                        {"brahl_context_path": ctx.get("context_path"), "purpose": prompt, "prompt": prompt},
                    )
            except Exception:
                pass

        return get_project(project_id) or p
    raise KeyError(project_id)
