"""Shared AI context documents — global across all projects (not per-project).

Built-in Docs/* are read-only. User docs live under qoa_web/data/user_ai_docs/
with a sidecar manifest.json (titles + in_prompt flags).
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]
USER_DOCS_DIR = KK_ROOT / "qoa_web" / "data" / "user_ai_docs"
USER_MANIFEST = USER_DOCS_DIR / "manifest.json"

MAX_USER_DOCS = 10
MAX_USER_FILE_BYTES = 12 * 1024
MAX_USER_PROMPT_CHARS = 3000
USER_PROMPT_CHARS_EACH = 1500

# Canonical .md files shown in AI docs viewer (skills, rules, BRAHL, FoXYiZ, README).
# Only `in_prompt: True` docs are packed into LLM system context — keep those SHORT.
# Master (everyone) = guardrails + brahl-prompt. Journey (this project) is virtual + always packed.
JOURNEY_DOC_ID = "journey"
JOURNEY_PROMPT_CHARS = 1600

AI_CONTEXT_DOCS: list[dict[str, Any]] = [
    {
        "id": "guardrails",
        "title": "Master · AI guardrails",
        "subtitle": "Everyone · token budgets · never Run/Loop LLM · BRAHL spelling",
        "path": "Docs/AI_GUARDRAILS.md",
        "kind": "master",
        "in_prompt": True,
        "prompt_chars": 2200,
        "master": True,
    },
    {
        "id": "brahl-prompt",
        "title": "Master · BRAHL (prompt)",
        "subtitle": "Everyone · slim lifecycle context for in-app AI",
        "path": "Docs/BRAHL_PROMPT.md",
        "kind": "master",
        "in_prompt": True,
        "prompt_chars": 2800,
        "master": True,
    },
    {
        "id": "brahl",
        "title": "BRAHL",
        "subtitle": "Full Build · Run · Analyze · Heal · Loop reference",
        "path": "Docs/BRAHL.md",
        "kind": "skill",
        "in_prompt": False,
    },
    {
        "id": "foxyiz",
        "title": "FoXYiZ",
        "subtitle": "f(x,y)=z automation skill · yPAD contract",
        "path": "Docs/FoXYiZ.md",
        "kind": "skill",
        "in_prompt": False,
    },
    {
        "id": "byok",
        "title": "Desktop BYOK",
        "subtitle": "User-owned OpenAI key · hosted quota mode",
        "path": "Docs/BRAHL_DESKTOP_BYOK.md",
        "kind": "rules",
        "in_prompt": False,
    },
    {
        "id": "rules",
        "title": "Agent rules",
        "subtitle": "Team conventions · Playwright · Heal scope",
        "path": "Docs/rules.md",
        "kind": "rules",
        "in_prompt": False,
    },
    {
        "id": "foxyiz-engine-readme",
        "title": "FoXYiZ engine guide",
        "subtitle": "Skills · memory · yPAD efficiency · AI rules",
        "path": "FoXYiZ/FoXYiZ_Readme.md",
        "kind": "readme",
        "in_prompt": False,
    },
    {
        "id": "brahl-web-readme",
        "title": "BRAHL Web README",
        "subtitle": "qoa_web local app · API · verify",
        "path": "qoa_web/README.md",
        "kind": "readme",
        "in_prompt": False,
    },
    {
        "id": "qoa-user-doc",
        "title": "BRAHL Web user guide",
        "subtitle": "End users & AI — personas, phases, Creator vs QA Hunter",
        "path": "qoa_web/qoa_userDoc.md",
        "kind": "readme",
        "in_prompt": False,
    },
    {
        "id": "test-user-data",
        "title": "Test user data",
        "subtitle": "Fictional personas P1–P9 · Creator & QA Hunter",
        "path": "Docs/test-user-data/README.md",
        "kind": "reference",
        "in_prompt": False,
    },
    {
        "id": "deploy",
        "title": "Deploy",
        "subtitle": "VPS / launch checklist",
        "path": "Docs/DEPLOY.md",
        "kind": "reference",
        "in_prompt": False,
    },
    {
        "id": "today-summary",
        "title": "Today's summary",
        "subtitle": "Latest session key changes",
        "path": "todaysummary.md",
        "kind": "readme",
        "in_prompt": False,
    },
]


def build_project_journey_md(project: dict[str, Any] | None) -> str:
    """Living per-project context — regenerated from project state on each AI call."""
    if not project:
        return (
            "# Journey (no project selected)\n\n"
            "Select a project in Arena so AI can follow purpose, phase, yPAD, and latest run.\n"
        )

    suite = str(project.get("suite_name") or project.get("name") or "project")
    purpose = (project.get("purpose") or project.get("prompt") or "").strip()
    app_url = (project.get("app_url") or "").strip()
    phase = str(project.get("current_phase") or project.get("phase") or "build").lower()
    cycle = project.get("phase_cycle") or project.get("brahl_cycle") or {}
    latest_run = project.get("latest_run") or project.get("last_run_name") or ""
    budget = float(project.get("budget_usd") or 0)
    runtime = project.get("runtime_mode") or "desktop"
    notes = (project.get("ai_journey_notes") or "").strip()
    go_nogo = project.get("brahl_decision") or project.get("go_nogo") or ""
    updated = project.get("updated_at") or project.get("ai_journey_updated_at") or ""

    # Phase event trail from cycle_history (newest first in store — reverse for chronology)
    events = project.get("cycle_history") or project.get("phase_events") or []
    event_lines: list[str] = []
    if isinstance(events, list):
        for ev in reversed(events[:6]):
            if not isinstance(ev, dict):
                continue
            label = ev.get("step") or ev.get("phase") or ev.get("kind") or ev.get("label") or "?"
            ts = (ev.get("at") or ev.get("ts") or "")[:19]
            detail = (ev.get("detail") or ev.get("note") or "")[:80]
            stats = ev.get("stats") or {}
            extra = ""
            if isinstance(stats, dict) and (stats.get("total_plans") or stats.get("fails") is not None):
                extra = (
                    f" · {stats.get('passes', 0)}/{stats.get('total_plans', '?')} pass, "
                    f"{stats.get('fails', 0)} fail"
                )
            event_lines.append(f"- {ts} · {label}" + (f" — {detail}" if detail else "") + extra)

    # yPAD / connectors hints from project fields when present
    ypad = project.get("ypad_summary") or {}
    plans = ypad.get("plans") if isinstance(ypad, dict) else None
    actions = ypad.get("actions") if isinstance(ypad, dict) else None
    designs = ypad.get("designs") if isinstance(ypad, dict) else None
    if plans is None:
        plans = project.get("ypad_plans_count")
    if actions is None:
        actions = project.get("ypad_actions_count")
    if designs is None:
        designs = project.get("ypad_designs_count")
    # Live recount from suite CSVs when missing
    if plans is None or actions is None or designs is None:
        try:
            import ypad as ypad_store

            suite_cfg = project.get("suite_config") or f"y/{suite}"
            for sheet, key in (("y1Plans", "plans"), ("y2Actions", "actions"), ("y3Designs", "designs")):
                if (key == "plans" and plans is not None) or (
                    key == "actions" and actions is not None
                ) or (key == "designs" and designs is not None):
                    continue
                try:
                    data = ypad_store.read_ypad_sheet(suite_cfg, sheet)
                    rows = data.get("rows") if isinstance(data, dict) else data
                    n = len(rows) if isinstance(rows, list) else 0
                    if key == "plans":
                        plans = n
                    elif key == "actions":
                        actions = n
                    else:
                        designs = n
                except Exception:
                    pass
        except Exception:
            pass

    ctx_items = project.get("context_items") or []
    ctx_labels = []
    for c in (ctx_items if isinstance(ctx_items, list) else [])[:8]:
        if isinstance(c, dict):
            ctx_labels.append(str(c.get("label") or c.get("kind") or "item"))

    cycle_bits = []
    if isinstance(cycle, dict) and cycle:
        for key in ("build", "run", "analyze", "heal", "loop"):
            if key in cycle:
                cycle_bits.append(f"{key}={cycle.get(key)}")

    lines = [
        f"# Journey · {suite}",
        "",
        f"- **Project:** {project.get('name') or suite} (`{project.get('id') or ''}`)",
        f"- **Suite:** `y/{suite}/`",
        f"- **Phase now:** {phase}",
        f"- **Runtime:** {runtime}",
        f"- **App URL:** {app_url or '(not set)'}",
        f"- **Budget:** ${budget:.0f}",
        f"- **Latest run:** {latest_run or '(none yet)'}",
    ]
    if go_nogo:
        lines.append(f"- **BRAHL decision:** {go_nogo}")
    if plans is not None or actions is not None or designs is not None:
        lines.append(
            f"- **yPAD:** plans={plans if plans is not None else '?'} · "
            f"actions={actions if actions is not None else '?'} · "
            f"designs={designs if designs is not None else '?'}"
        )
    if cycle_bits:
        lines.append(f"- **Cycle markers:** {', '.join(cycle_bits)}")
    if ctx_labels:
        lines.append(f"- **Connectors / context:** {', '.join(ctx_labels)}")
    if updated:
        lines.append(f"- **Updated:** {str(updated)[:19]}")
    lines.extend(["", "## Purpose", purpose[:900] if purpose else "(none yet — set purpose in Build)"])
    if event_lines:
        lines.extend(["", "## Recent phases", *event_lines])
    if notes:
        lines.extend(["", "## User journey notes", notes[:500]])
    lines.extend(
        [
            "",
            "## AI must",
            "- Stay aligned with this project purpose and current phase.",
            "- Prefer yPAD edits (Build/Heal) over inventing app code or locators.",
            "- Send execution to Run/Loop — never claim to have run FoXYiZ yourself.",
        ]
    )
    return "\n".join(lines) + "\n"


def journey_doc_meta(project: dict[str, Any] | None = None) -> dict[str, Any]:
    name = (project or {}).get("name") or (project or {}).get("suite_name") or "this project"
    body = build_project_journey_md(project)
    return {
        "id": JOURNEY_DOC_ID,
        "title": f"Journey · {name}",
        "subtitle": "This project · auto-updates as you Build / Run / Analyze / Heal / Loop",
        "path": f"project://{((project or {}).get('id') or 'none')}/journey.md",
        "kind": "journey",
        "in_prompt": True,
        "exists": True,
        "size_bytes": len(body.encode("utf-8")),
        "source": "journey",
        "editable": False,
        "master": False,
        "prompt_chars": JOURNEY_PROMPT_CHARS,
        "content": body,
    }


def _resolve(rel: str) -> Path:
    return KK_ROOT / rel.replace("/", "\\")


def _invalidate_prompt_cache() -> None:
    try:
        import ai_assist

        ai_assist.invalidate_doc_cache()
    except Exception:
        pass


def _ensure_user_dir() -> None:
    USER_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    if not USER_MANIFEST.is_file():
        USER_MANIFEST.write_text(
            json.dumps({"version": 1, "docs": []}, indent=2) + "\n",
            encoding="utf-8",
        )


def _load_manifest() -> dict[str, Any]:
    _ensure_user_dir()
    try:
        data = json.loads(USER_MANIFEST.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"version": 1, "docs": []}
        data.setdefault("version", 1)
        data.setdefault("docs", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "docs": []}


def _save_manifest(data: dict[str, Any]) -> None:
    _ensure_user_dir()
    USER_MANIFEST.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    _invalidate_prompt_cache()


def _safe_user_file(doc_id: str) -> Path | None:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", doc_id or ""):
        return None
    path = (USER_DOCS_DIR / f"{doc_id}.md").resolve()
    try:
        path.relative_to(USER_DOCS_DIR.resolve())
    except ValueError:
        return None
    return path


def _slug_title(title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "-", (title or "note").strip().lower()).strip("-")
    base = (base or "note")[:40]
    return f"u-{base}-{uuid.uuid4().hex[:6]}"


def list_builtin_docs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in AI_CONTEXT_DOCS:
        path = _resolve(spec["path"])
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        out.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "subtitle": spec.get("subtitle", ""),
                "path": spec["path"],
                "kind": spec.get("kind", "doc"),
                "in_prompt": bool(spec.get("in_prompt")),
                "exists": exists,
                "size_bytes": size,
                "source": "builtin",
                "editable": False,
                "master": bool(spec.get("master")),
            }
        )
    return out


def list_user_docs() -> list[dict[str, Any]]:
    man = _load_manifest()
    out: list[dict[str, Any]] = []
    for entry in man.get("docs") or []:
        doc_id = str(entry.get("id") or "")
        path = _safe_user_file(doc_id)
        if not path:
            continue
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        rel = f"qoa_web/data/user_ai_docs/{doc_id}.md"
        out.append(
            {
                "id": doc_id,
                "title": entry.get("title") or doc_id,
                "subtitle": entry.get("subtitle") or "My doc",
                "path": rel,
                "kind": "user",
                "in_prompt": bool(entry.get("in_prompt")),
                "exists": exists,
                "size_bytes": size,
                "source": "user",
                "editable": True,
                "prompt_chars": int(entry.get("prompt_chars") or USER_PROMPT_CHARS_EACH),
            }
        )
    return out


def list_ai_docs(project: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Master (everyone) + living Journey (this project) + optional My docs."""
    journey = journey_doc_meta(project)
    journey_list = [{k: v for k, v in journey.items() if k != "content"}]
    return journey_list + list_builtin_docs() + list_user_docs()


def user_prompt_budget() -> dict[str, Any]:
    """Chars currently reserved for user in_prompt docs vs hard cap."""
    used = 0
    for d in list_user_docs():
        if not d.get("in_prompt") or not d.get("exists"):
            continue
        path = _safe_user_file(d["id"])
        if not path or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        cap = min(int(d.get("prompt_chars") or USER_PROMPT_CHARS_EACH), MAX_USER_PROMPT_CHARS)
        used += min(len(text), cap)
    return {
        "used_chars": used,
        "max_chars": MAX_USER_PROMPT_CHARS,
        "over_budget": used > MAX_USER_PROMPT_CHARS,
        "max_docs": MAX_USER_DOCS,
        "max_file_bytes": MAX_USER_FILE_BYTES,
        "doc_count": len(list_user_docs()),
    }


def get_ai_doc(doc_id: str, project: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if doc_id == JOURNEY_DOC_ID:
        return journey_doc_meta(project)
    spec = next((d for d in AI_CONTEXT_DOCS if d["id"] == doc_id), None)
    if spec:
        path = _resolve(spec["path"])
        if not path.is_file():
            return {
                **spec,
                "content": f"# Missing\n\nFile not found: `{spec['path']}`",
                "exists": False,
                "source": "builtin",
                "editable": False,
                "master": bool(spec.get("master")),
            }
        content = path.read_text(encoding="utf-8")
        return {
            "id": spec["id"],
            "title": spec["title"],
            "subtitle": spec.get("subtitle", ""),
            "path": spec["path"],
            "kind": spec.get("kind", "doc"),
            "in_prompt": bool(spec.get("in_prompt")),
            "exists": True,
            "content": content,
            "source": "builtin",
            "editable": False,
            "master": bool(spec.get("master")),
        }

    man = _load_manifest()
    entry = next((d for d in (man.get("docs") or []) if d.get("id") == doc_id), None)
    path = _safe_user_file(doc_id)
    if not entry or not path:
        return None
    exists = path.is_file()
    content = path.read_text(encoding="utf-8") if exists else ""
    return {
        "id": doc_id,
        "title": entry.get("title") or doc_id,
        "subtitle": entry.get("subtitle") or "My doc",
        "path": f"qoa_web/data/user_ai_docs/{doc_id}.md",
        "kind": "user",
        "in_prompt": bool(entry.get("in_prompt")),
        "exists": exists,
        "content": content,
        "source": "user",
        "editable": True,
        "prompt_chars": int(entry.get("prompt_chars") or USER_PROMPT_CHARS_EACH),
    }


def create_user_doc(
    title: str,
    content: str = "",
    *,
    in_prompt: bool = False,
    subtitle: str = "",
) -> dict[str, Any]:
    man = _load_manifest()
    docs = list(man.get("docs") or [])
    if len(docs) >= MAX_USER_DOCS:
        raise ValueError(f"At most {MAX_USER_DOCS} user docs allowed")
    body = content or f"# {title or 'My notes'}\n\n"
    raw = body.encode("utf-8")
    if len(raw) > MAX_USER_FILE_BYTES:
        raise ValueError(f"Doc exceeds {MAX_USER_FILE_BYTES} bytes")
    doc_id = _slug_title(title or "note")
    path = _safe_user_file(doc_id)
    if not path:
        raise ValueError("Invalid document id")
    path.write_text(body, encoding="utf-8")
    entry = {
        "id": doc_id,
        "title": (title or "My notes").strip()[:120],
        "subtitle": (subtitle or "My doc").strip()[:160],
        "in_prompt": bool(in_prompt),
        "prompt_chars": USER_PROMPT_CHARS_EACH,
    }
    if in_prompt:
        _assert_user_prompt_ok(docs + [entry], {doc_id: body})
    docs.append(entry)
    man["docs"] = docs
    _save_manifest(man)
    return get_ai_doc(doc_id)  # type: ignore[return-value]


def update_user_doc(
    doc_id: str,
    *,
    title: str | None = None,
    content: str | None = None,
    in_prompt: bool | None = None,
    subtitle: str | None = None,
) -> dict[str, Any]:
    man = _load_manifest()
    docs = list(man.get("docs") or [])
    idx = next((i for i, d in enumerate(docs) if d.get("id") == doc_id), None)
    if idx is None:
        raise FileNotFoundError(f"User doc not found: {doc_id}")
    path = _safe_user_file(doc_id)
    if not path:
        raise ValueError("Invalid document id")
    entry = dict(docs[idx])
    if title is not None:
        entry["title"] = title.strip()[:120] or entry.get("title") or doc_id
    if subtitle is not None:
        entry["subtitle"] = subtitle.strip()[:160]
    if in_prompt is not None:
        entry["in_prompt"] = bool(in_prompt)
    body = content
    if content is not None:
        raw = content.encode("utf-8")
        if len(raw) > MAX_USER_FILE_BYTES:
            raise ValueError(f"Doc exceeds {MAX_USER_FILE_BYTES} bytes")
        path.write_text(content, encoding="utf-8")
        body = content
    elif path.is_file():
        body = path.read_text(encoding="utf-8")
    else:
        body = ""
    docs[idx] = entry
    if entry.get("in_prompt"):
        bodies = {doc_id: body or ""}
        for d in docs:
            if d.get("id") == doc_id:
                continue
            if not d.get("in_prompt"):
                continue
            p = _safe_user_file(str(d.get("id")))
            if p and p.is_file():
                bodies[str(d["id"])] = p.read_text(encoding="utf-8")
        _assert_user_prompt_ok(docs, bodies)
    man["docs"] = docs
    _save_manifest(man)
    return get_ai_doc(doc_id)  # type: ignore[return-value]


def delete_user_doc(doc_id: str) -> None:
    man = _load_manifest()
    docs = list(man.get("docs") or [])
    new_docs = [d for d in docs if d.get("id") != doc_id]
    if len(new_docs) == len(docs):
        raise FileNotFoundError(f"User doc not found: {doc_id}")
    path = _safe_user_file(doc_id)
    if path and path.is_file():
        path.unlink()
    man["docs"] = new_docs
    _save_manifest(man)


def _assert_user_prompt_ok(docs: list[dict[str, Any]], bodies: dict[str, str]) -> None:
    used = 0
    for d in docs:
        if not d.get("in_prompt"):
            continue
        text = bodies.get(str(d.get("id")), "")
        cap = min(int(d.get("prompt_chars") or USER_PROMPT_CHARS_EACH), MAX_USER_PROMPT_CHARS)
        used += min(len(text), cap)
    if used > MAX_USER_PROMPT_CHARS:
        raise ValueError(
            f"User in-prompt docs exceed {MAX_USER_PROMPT_CHARS} chars "
            f"(would use ~{used}). Turn some off or shorten."
        )


def prompt_doc_paths() -> list[str]:
    paths = [d["path"] for d in AI_CONTEXT_DOCS if d.get("in_prompt")]
    for d in list_user_docs():
        if d.get("in_prompt") and d.get("exists"):
            paths.append(d["path"])
    return paths


def prompt_doc_specs(project: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Docs eligible for LLM packing, with optional per-doc char caps.

    Order: Journey (this project) → Master (everyone) → opted-in My docs.
    """
    specs: list[dict[str, Any]] = []
    if project is not None:
        specs.append(
            {
                "id": JOURNEY_DOC_ID,
                "title": "Journey",
                "path": "",
                "in_prompt": True,
                "prompt_chars": JOURNEY_PROMPT_CHARS,
                "source": "journey",
                "content": build_project_journey_md(project),
            }
        )
    specs.extend([d for d in AI_CONTEXT_DOCS if d.get("in_prompt")])
    user_budget_left = MAX_USER_PROMPT_CHARS
    for d in list_user_docs():
        if not d.get("in_prompt") or not d.get("exists"):
            continue
        cap = min(int(d.get("prompt_chars") or USER_PROMPT_CHARS_EACH), user_budget_left)
        if cap <= 0:
            break
        specs.append(
            {
                "id": d["id"],
                "title": d["title"],
                "path": d["path"],
                "in_prompt": True,
                "prompt_chars": cap,
                "source": "user",
            }
        )
        user_budget_left -= cap
    return specs
