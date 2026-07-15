"""Generate structured BRAHL Plans from requirements (qoa2-style)."""

from __future__ import annotations

import json
import re
from typing import Any

from ai_assist import chat_metered, is_ai_available


def _fallback_plan(requirement: str) -> dict[str, Any]:
    """Scripted plan when AI is unavailable."""
    stories = [
        {"title": "Happy path smoke", "description": "Core user journey works end-to-end", "automated": True},
        {"title": "Auth & session", "description": "Login, logout, session persistence", "automated": True},
        {"title": "Mobile viewport", "description": "Layout on phone — manual on real device", "automated": False},
        {"title": "Edge case inputs", "description": "Empty, long, special characters", "automated": True},
        {"title": "QA Hunter exploration", "description": "UX and accessibility pass", "automated": False},
    ]
    tests = [
        {"id": f"T{i + 1}", "title": f"Test case {i + 1}", "automated": i % 3 != 2}
        for i in range(12)
    ]
    auto = sum(1 for t in tests if t.get("automated"))
    return {
        "summary": requirement[:500] or "Test strategy for MVP launch",
        "user_stories": stories,
        "test_cases": tests,
        "automated_count": auto,
        "manual_count": len(tests) - auto,
        "run_how": "Run FoXYiZ fEngine2 locally or on server — Tests / Steps / Test data CSVs in y/<suite>/",
    }


def generate_brahl_plan(
    requirement: str,
    project_name: str = "project",
    app_url: str = "",
    budget_usd: float = 0,
) -> dict[str, Any]:
    requirement = (requirement or "").strip()
    if not requirement:
        raise ValueError("Requirement text required")

    if not is_ai_available():
        plan = _fallback_plan(requirement)
        md = _plan_to_markdown(plan)
        return {"brahl_plan": plan, "preview_markdown": md, "ai": False}

    system = (
        "You are a QA architect for QAonAir BRAHL (Build Run Analyze Heal Loop).\n"
        "Generate a structured test plan as JSON only — no markdown fences.\n"
        "Schema:\n"
        '{"summary":"...", "user_stories":[{"title":"...","description":"...","automated":true|false}], '
        '"test_cases":[{"id":"T1","title":"...","automated":true|false}], '
        '"automated_count":N, "manual_count":M, '
        '"run_how":"Execute via FoXYiZ fEngine2 — low-code Tests/Steps/Test data CSVs. No Playwright."}\n'
        "Target ~5 user_stories and ~12 test_cases. Mark mobile/real-device/UX as manual (automated:false).\n"
        "FoXYiZ automates; QA Hunters cover manual-only scenarios."
    )
    user = (
        f"Project: {project_name}\nApp URL: {app_url or 'not set'}\nBudget: ${budget_usd:.0f}\n\n"
        f"Requirement:\n{requirement}"
    )
    raw, _meta = chat_metered(system, user, role="planner", max_tokens=900)
    plan = _parse_plan_json(raw) if raw else None
    if not plan:
        plan = _fallback_plan(requirement)
    if "automated_count" not in plan:
        plan["automated_count"] = sum(1 for t in plan.get("test_cases", []) if t.get("automated"))
    if "manual_count" not in plan:
        plan["manual_count"] = len(plan.get("test_cases", [])) - plan["automated_count"]
    md = _plan_to_markdown(plan)
    return {"brahl_plan": plan, "preview_markdown": md, "ai": True}


def _parse_plan_json(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _plan_to_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"## BRAHL Plan\n\n{plan.get('summary', '')}\n",
        f"**{plan.get('automated_count', 0)}** automated · **{plan.get('manual_count', 0)}** manual test cases\n",
        "### User stories\n",
    ]
    for s in plan.get("user_stories") or []:
        tag = "FoXYiZ" if s.get("automated") else "QA Hunter"
        lines.append(f"- **{s.get('title', '')}** ({tag}) — {s.get('description', '')}")
    lines.append("\n### Test cases\n")
    for t in plan.get("test_cases") or []:
        tag = "auto" if t.get("automated") else "manual"
        lines.append(f"- {t.get('id', '')} {t.get('title', '')} [{tag}]")
    if plan.get("run_how"):
        lines.append(f"\n### Run\n\n{plan['run_how']}")
    return "\n".join(lines)
