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
KK_ROOT = Path(__file__).resolve().parents[2]
Z_DIR = KK_ROOT / "z"

REPORT_SOURCE_LABELS = {
    "automation": "Automation",
    "automation_ai": "Automation + AI",
    "human_in_the_loop": "Human in the Loop",
    "human_ai": "Human + AI",
    "human_automation": "Human + Automation",
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
    project.setdefault("ai_enabled", True)
    project.setdefault("cycle_history", [])
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
    if not project.get("prompt") and project.get("purpose"):
        project["prompt"] = project["purpose"]
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


def list_client_projects() -> list[dict[str, Any]]:
    return [p for p in load_projects() if p.get("owner_avatar") == "client"]


def list_consultant_projects() -> list[dict[str, Any]]:
    return [
        p
        for p in load_projects()
        if p.get("owner_avatar") == "client" and p.get("status") in ("open", "in_progress")
    ]


def create_project(body: dict[str, Any]) -> dict[str, Any]:
    projects = load_projects()
    name = body.get("name", "").strip() or "Untitled project"
    purpose = body.get("purpose", body.get("prompt", "")).strip()
    project = _normalize(
        {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "app_url": body.get("app_url", "").strip(),
            "purpose": purpose,
            "prompt": purpose,
            "owner_avatar": "client",
            "status": "open",
            "documents": [],
            "context_items": [],
            "chat_messages": [],
            "budget_usd": float(body.get("budget_usd") or 0),
            "budget_split": body.get("budget_split")
            or {"automation_pct": 50, "human_pct": 50},
            "hitl_consultants": [],
            "reports": [],
            "ai_enabled": body.get("ai_enabled", True),
            "brahl_context_path": body.get("brahl_context_path"),
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
        }
        for key, val in patch.items():
            if key in allowed:
                p[key] = val
        if "purpose" in patch:
            p["prompt"] = p.get("purpose") or ""
        p["updated_at"] = _now()
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
        history = list(p.get("cycle_history") or [])
        history.insert(0, entry)
        p["cycle_history"] = history[:50]
        p["updated_at"] = _now()
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


def assistant_reply(project: dict[str, Any], user_text: str) -> str:
    """Scripted Build assistant — purpose, connectors, budget."""
    msgs = [m for m in project.get("chat_messages", []) if m.get("role") == "user"]
    ctx_count = len(project.get("context_items") or [])
    budget = float(project.get("budget_usd") or 0)
    lower = user_text.lower().strip()

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
            "(AI + FoXYiZ) and Human in the Loop consultants who enrich reports offline."
        )
    hitl = len(project.get("hitl_consultants") or [])
    if hitl == 0:
        return (
            f"Budget ${budget:.0f} noted ({project['budget_split']['automation_pct']}% automation / "
            f"{project['budget_split']['human_pct']}% Human in the Loop). "
            "Consultants can join when you're ready. Use Loop to capture Step 0 context."
        )
    return (
        f"{hitl} Human in the Loop consultant(s) active. "
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


def join_hitl(project_id: str, consultant_name: str = "Consultant") -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        team = list(p.get("hitl_consultants") or [])
        if any(c.get("id") == HITL_CONSULTANT_ID for c in team):
            return p
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


def submit_hitl_report(
    project_id: str,
    run_name: str,
    report_path: str | None = None,
    *,
    critical_issues: int = 0,
    time_hours: float = 0.0,
    features_found: int = 0,
) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        reports = list(p.get("reports") or [])
        # AI off: HITL runs FoXYiZ locally, uploads Automation + AI reports
        report_source = (
            "automation_ai"
            if p.get("ai_enabled") is False
            else "human_in_the_loop"
        )
        entry = {
            "run_name": run_name,
            "report_path": report_path,
            "submitted_at": _now(),
            "source": report_source,
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
) -> dict[str, Any]:
    projects = load_projects()
    for i, p in enumerate(projects):
        if p.get("id") != project_id:
            continue
        p = _normalize(p)
        reports = list(p.get("reports") or [])
        for r in reports:
            if r.get("run_name") == run_name:
                return r
        path = report_path or (
            f"z/{run_name}/brahl_report.md" if _resolve_report_file(run_name) else None
        )
        entry = {
            "id": uuid.uuid4().hex[:8],
            "run_name": run_name,
            "report_path": path,
            "submitted_at": _now(),
            "source": source if source in REPORT_SOURCE_LABELS else "automation",
        }
        reports.append(entry)
        p["reports"] = reports
        p["latest_run"] = run_name
        p["updated_at"] = _now()
        projects[i] = p
        save_projects(projects)
        return entry
    raise KeyError(project_id)


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
        enriched.append(
            {
                **r,
                "source": src,
                "source_label": REPORT_SOURCE_LABELS.get(src, src),
                "has_file": path is not None,
            }
        )
    enriched.sort(key=lambda x: x.get("submitted_at") or "", reverse=True)
    return enriched


def load_report_markdown(run_name: str) -> str:
    path = _resolve_report_file(run_name)
    if not path:
        raise FileNotFoundError(run_name)
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_section(md: str, heading: str) -> str:
    marker = f"## {heading}"
    if marker not in md:
        return ""
    part = md.split(marker, 1)[1]
    nxt = part.find("\n## ")
    return (part[:nxt] if nxt >= 0 else part).strip()[:1200]


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


def brahl_model_reply(project: dict[str, Any], report_md: str | None, user_text: str) -> str:
    """BRAHL model — scoped to active project and latest report only."""
    name = project.get("name") or "this project"
    purpose = project.get("purpose") or project.get("prompt") or "No purpose captured yet."
    lower = user_text.lower().strip()
    reports = project.get("reports") or []

    if not report_md:
        return (
            f"No BRAHL report file yet for **{name}**. "
            f"Run Loop → Verify or have a Human in the Loop consultant submit a report. "
            f"Project purpose: {purpose[:200]}"
        )

    summary = _extract_section(report_md, "Executive summary") or report_md[:600]

    if any(w in lower for w in ("summary", "executive", "overview")):
        return f"**{name}** — Executive summary from the latest BRAHL report:\n\n{summary}"

    if any(w in lower for w in ("fail", "issue", "defect", "bug")):
        section = _extract_section(report_md, "Customer action plan") or _extract_section(report_md, "Failures")
        if section:
            return f"**{name}** — Issues / action items:\n\n{section}"
        return f"**{name}** — No dedicated failures section in this report. Summary:\n\n{summary[:500]}"

    if any(w in lower for w in ("human", "hitl", "consultant")):
        hitl = len(project.get("hitl_consultants") or [])
        human_reports = [r for r in reports if "human" in (r.get("source") or "")]
        return (
            f"**{name}** has {hitl} Human in the Loop consultant(s) and "
            f"{len(human_reports)} human-enriched report(s). "
            "Human reports add critical issues, UX findings, and offline yPAD work on top of automation."
        )

    if any(w in lower for w in ("automation", "ai", "verify")):
        auto = [r for r in reports if r.get("source") in ("automation", "automation_ai")]
        return (
            f"**{name}** — {len(auto)} automation/AI BRAHL report(s). "
            f"Latest verify context:\n\n{summary[:400]}"
        )

    if any(w in lower for w in ("purpose", "scope", "project")):
        return f"**{name}** purpose: {purpose}\n\nLatest BRAHL headline:\n{summary[:400]}"

    return (
        f"**{name}** — I only discuss this project and its BRAHL reports. "
        f"Ask about summary, failures, Human in the Loop, or automation. "
        f"Latest report excerpt:\n\n{summary[:350]}"
    )
