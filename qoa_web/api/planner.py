"""AI planner chat for Create challenge → yPAD scaffold → optional quick BRAHL."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from ai_assist import chat_metered, is_ai_available, brahl_doc_context
from brahl_plan import generate_brahl_plan
from runner import create_ypad_suite, default_fstart_for_suite, slug_suite_name
import projects as project_store


def _extract_url(text: str) -> str:
    m = re.search(r"https?://[^\s<>\"']+", text or "", re.I)
    return (m.group(0).rstrip(").,;]") if m else "").strip()


def _guess_name(url: str, text: str) -> str:
    if url:
        host = urlparse(url).hostname or ""
        host = host.lower().removeprefix("www.")
        part = host.split(".")[0] if host else ""
        if part and part not in ("localhost", "127"):
            return slug_suite_name(part)
    words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", text or "")
    for w in words:
        low = w.lower()
        if low in ("https", "http", "www", "the", "and", "for", "this", "that", "with", "from", "build", "test"):
            continue
        return slug_suite_name(w)
    return "new_app"


def _merge_draft(draft: dict[str, Any] | None, user_text: str) -> dict[str, Any]:
    d = dict(draft or {})
    text = (user_text or "").strip()
    url = _extract_url(text)
    if url:
        d["app_url"] = url
    if not d.get("name"):
        d["name"] = _guess_name(d.get("app_url") or url, text)
    # Keep building purpose from free text (skip if message is only a URL)
    if text and text != url:
        purpose = (d.get("purpose") or "").strip()
        if purpose and text not in purpose:
            d["purpose"] = f"{purpose}\n{text}".strip()
        else:
            d["purpose"] = text if not purpose else purpose
    if not d.get("purpose") and (d.get("app_url") or url):
        d["purpose"] = f"Smoke + launch readiness BRAHL for {d.get('app_url') or url}"
    d.setdefault("budget_usd", 50)
    d.setdefault("ai_enabled", True)
    name_ok = bool((d.get("name") or "").strip())
    url_ok = bool((d.get("app_url") or "").strip())
    purpose_ok = len((d.get("purpose") or "").strip()) >= 12
    d["ready"] = name_ok and url_ok and purpose_ok
    d["missing"] = [k for k, ok in (("name", name_ok), ("app_url", url_ok), ("purpose", purpose_ok)) if not ok]
    return d


def _fallback_reply(draft: dict[str, Any], user_text: str) -> str:
    if not draft.get("app_url"):
        return (
            "Tell me the **app URL** (or paste it), and what you want covered — "
            "e.g. checkout, login, landing. I will draft a lean BRAHL strategy and yPAD white sheets."
        )
    if not draft.get("purpose") or draft.get("purpose") == user_text and len(user_text) < 20:
        return (
            f"Got **{draft.get('app_url')}**. What should we focus on for launch — "
            "smoke paths, payments, auth, or full e-commerce flows?"
        )
    if draft.get("ready"):
        return (
            f"Ready to create **{draft.get('name')}** for `{draft.get('app_url')}`.\n\n"
            "I will scaffold Tests / Steps / Test data (yPAD), generate a BRAHL Plan, "
            "then you can **Create & quick BRAHL** for a Go/No-Go scorecard.\n\n"
            "Say **create** or click the button below."
        )
    missing = ", ".join(draft.get("missing") or [])
    return f"Almost there — still need: **{missing}**. Reply with those details (or speak them)."


def planner_turn(
    message: str,
    draft: dict[str, Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    merged = _merge_draft(draft, message)
    reply = None
    if is_ai_available():
        system = (
            "You are the BRAHL Create Planner for QAonAir. Guide Creators in a short chat to define: "
            "project name (folder slug), app URL, and purpose/requirements. "
            "Then explain you will build lean yPAD white pads (plans, steps, test data) and a BRAHL strategy. "
            "Be concise (≤120 words). Always use the spelling BRAHL (never brawl). "
            "When draft is ready, tell them to click Create & quick BRAHL.\n\n"
            + brahl_doc_context(role="planner")
        )
        user = (
            f"Current draft JSON: {merged}\n\n"
            f"User message: {message}\n\n"
            "Reply in plain text (no JSON)."
        )
        reply, _meta = chat_metered(system, user, history, role="planner")
    if not reply:
        reply = _fallback_reply(merged, message)

    plan_preview = None
    if merged.get("ready") and (merged.get("purpose") or "").strip():
        try:
            gen = generate_brahl_plan(
                merged["purpose"],
                project_name=merged.get("name") or "project",
                app_url=merged.get("app_url") or "",
                budget_usd=float(merged.get("budget_usd") or 0),
            )
            plan_preview = {
                "summary": (gen.get("brahl_plan") or {}).get("summary"),
                "automated_count": (gen.get("brahl_plan") or {}).get("automated_count"),
                "manual_count": (gen.get("brahl_plan") or {}).get("manual_count"),
                "preview_markdown": gen.get("preview_markdown"),
                "brahl_plan": gen.get("brahl_plan"),
                "ai": gen.get("ai"),
            }
        except Exception:
            plan_preview = None

    return {
        "reply": reply,
        "draft": merged,
        "plan_preview": plan_preview,
        "ai": is_ai_available(),
    }


def create_from_planner(
    draft: dict[str, Any],
    brahl_plan: dict[str, Any] | None = None,
    owner_user_id: str | None = None,
) -> dict[str, Any]:
    from runner import capture_brahl_context

    name = slug_suite_name((draft.get("name") or "").strip())
    app_url = (draft.get("app_url") or "").strip()
    purpose = (draft.get("purpose") or "").strip()
    if not name:
        raise ValueError("Project name required")
    if not app_url:
        raise ValueError("App URL required")
    # Prefer plan attached on draft path; ensure strategy exists for white pads
    plan = brahl_plan
    if not plan and purpose:
        try:
            gen = generate_brahl_plan(
                purpose,
                project_name=name,
                app_url=app_url,
                budget_usd=float(draft.get("budget_usd") or 0),
            )
            plan = gen.get("brahl_plan")
        except Exception:
            plan = None

    detail = create_ypad_suite(name, app_url, purpose, brahl_plan=plan)
    safe = detail["name"]
    context_items = [{"kind": "url", "label": "App URL", "value": app_url}]
    project = project_store.create_project(
        {
            "name": safe,
            "app_url": app_url,
            "purpose": purpose,
            "prompt": purpose,
            "suite_name": safe,
            "suite_config": detail.get("path") or f"y/{safe}/{safe}.json",
            "budget_usd": float(draft.get("budget_usd") or 50),
            "ai_enabled": draft.get("ai_enabled", True) is not False,
            "context_items": context_items,
            "owner_user_id": owner_user_id,
            "brahl_plan_draft": plan,
        }
    )
    if plan:
        try:
            project = project_store.apply_brahl_plan(project["id"], plan, write_ypad=False)
        except Exception:
            pass
    fstart = detail.get("fstart_smoke") or default_fstart_for_suite(safe)

    # Step 0 — wire Origin prompt for BRAHL report
    try:
        ctx = capture_brahl_context(purpose or f"BRAHL for {app_url}", fstart)
        project = project_store.update_project(
            project["id"],
            {"brahl_context_path": ctx.get("context_path"), "prompt": purpose, "purpose": purpose},
        ) or project
    except Exception:
        pass

    return {
        "suite": detail,
        "project": project,
        "config_path": fstart,
        "ypad": detail.get("ypad"),
        "payout_preview": project_store.compute_payout_preview(project),
    }
