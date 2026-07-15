"""Suite test strategy.md / test plan.md — read from y/<suite>/ or synthesize."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from paths import Y_DIR
from runner import get_suite_detail

DOC_IDS = ("strategy", "plan")

DOC_META = {
    "strategy": {
        "id": "strategy",
        "filename": "test_strategy.md",
        "label": "test strategy.md",
        "title": "Test strategy",
        "blurb": "Why and how we test — purpose, approach, automation vs manual, BRAHL cycle.",
    },
    "plan": {
        "id": "plan",
        "filename": "test_plan.md",
        "label": "test plan.md",
        "title": "Test plan",
        "blurb": "What we test — yPAD plans, coverage counts, stories and cases.",
    },
}


def suite_y_dir(suite_name: str) -> Path:
    return Y_DIR / suite_name


def _doc_path(suite_name: str, doc_id: str) -> Path:
    return suite_y_dir(suite_name) / DOC_META[doc_id]["filename"]


def _synopsis(markdown: str, max_chars: int = 480) -> str:
    text = (markdown or "").strip()
    if not text:
        return ""
    lines = text.splitlines()
    # Drop title H1 and collect first prose under Purpose/Summary (or first non-heading)
    prose: list[str] = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            if prose:
                break
            continue
        if s.startswith("|") or s.startswith("---"):
            break
        # Strip light markdown for chip blurb
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"`([^`]+)`", r"\1", s)
        s = re.sub(r"^[-*]\s+", "", s)
        prose.append(s)
        if sum(len(x) for x in prose) >= max_chars:
            break
    chunk = " ".join(prose).strip()
    chunk = re.sub(r"\s+", " ", chunk)
    if len(chunk) <= max_chars:
        return chunk
    cut = chunk[:max_chars].rsplit(" ", 1)[0].rstrip(".,;")
    return cut + "…"


def _ypad_plan_rows(suite_name: str) -> list[dict[str, str]]:
    try:
        import ypad as ypad_store

        detail = get_suite_detail(suite_name) or {}
        cfg = detail.get("path") or f"y/{suite_name}/{suite_name}.json"
        sheet = ypad_store.read_ypad_sheet(cfg, "plans")
        return list(sheet.get("rows") or [])
    except Exception:
        return []


def _synthesize_strategy(
    suite_name: str,
    *,
    suite: dict[str, Any] | None,
    project: dict[str, Any] | None,
    plan_rows: list[dict[str, str]],
) -> str:
    suite = suite or {}
    project = project or {}
    draft = project.get("brahl_plan_draft") or {}
    purpose = (
        (draft.get("summary") or "").strip()
        or (project.get("purpose") or project.get("prompt") or "").strip()
        or (suite.get("description") or "").strip()
        or f"Launch readiness for {suite_name}."
    )
    app_url = (project.get("app_url") or suite.get("url") or "").strip()
    total = len(plan_rows)
    auto = sum(1 for r in plan_rows if (r.get("Run") or "").strip().upper() == "Y")
    manual = max(0, total - auto)
    if draft:
        auto = draft.get("automated_count", auto)
        manual = draft.get("manual_count", manual)
        total = auto + manual if isinstance(auto, int) and isinstance(manual, int) else total

    bullets = draft.get("strategy_bullets") or draft.get("strategy") or []
    bullet_lines: list[str] = []
    for b in bullets[:8]:
        if isinstance(b, str) and b.strip():
            bullet_lines.append(f"- {b.strip()}")
        elif isinstance(b, dict):
            t = (b.get("text") or b.get("title") or "").strip()
            if t:
                bullet_lines.append(f"- {t}")

    lines = [
        f"# Test strategy — {suite_name}",
        "",
        "## Purpose",
        "",
        purpose,
        "",
    ]
    if app_url:
        lines += ["## App under test", "", app_url, ""]
    lines += [
        "## Approach",
        "",
        "- **Automated** — FoXYiZ runs yPAD plans marked `Run=Y` (engine only; no LLM required).",
        "- **Manual** — QA Hunters cover `Run=N` UX, real-device, and exploratory gaps.",
        "- **AI (optional)** — assists Build / Analyze / Heal when AI is on; never replaces FoXYiZ Run.",
        "",
        "## Coverage posture",
        "",
        f"- **{auto}** automated · **{manual}** manual · **{total}** plans in scope (from yPAD / BRAHL draft).",
        "",
    ]
    if bullet_lines:
        lines += ["## Strategy notes", "", *bullet_lines, ""]
    lines += [
        "## BRAHL QA agent cycle",
        "",
        "1. **Build** — strategy, test plan, and yPAD (plans · steps · data).",
        "2. **Run** — FoXYiZ executes automated plans.",
        "3. **Analyze** — failures from `z/` (Input · Expected · Output).",
        "4. **Heal** — fix yPAD locators / steps / data.",
        "5. **Loop** — retry fails (up to 3×) · optional full Verify.",
        "6. **BRAHL** — Go/No-Go launch report.",
        "",
        f"_Source: `y/{suite_name}/{DOC_META['strategy']['filename']}` (synthesized if the file was missing)._",
    ]
    return "\n".join(lines)


def _synthesize_plan(
    suite_name: str,
    *,
    suite: dict[str, Any] | None,
    project: dict[str, Any] | None,
    plan_rows: list[dict[str, str]],
) -> str:
    suite = suite or {}
    project = project or {}
    draft = project.get("brahl_plan_draft") or {}
    purpose = (
        (draft.get("summary") or "").strip()
        or (project.get("purpose") or project.get("prompt") or "").strip()
        or (suite.get("description") or "").strip()
        or f"Test plan for {suite_name}."
    )
    total = len(plan_rows)
    auto = sum(1 for r in plan_rows if (r.get("Run") or "").strip().upper() == "Y")
    manual = max(0, total - auto)

    lines = [
        f"# Test plan — {suite_name}",
        "",
        "## Summary",
        "",
        purpose,
        "",
        "## Coverage",
        "",
        f"- **{auto}** automated (`Run=Y`) · **{manual}** manual (`Run=N`) · **{total}** plans in y1Plans.",
        "",
    ]

    stories = draft.get("user_stories") or []
    if stories:
        lines += ["## User stories", ""]
        for s in stories:
            tag = "automated" if s.get("automated") is not False else "manual"
            title = (s.get("title") or "Story").strip()
            desc = (s.get("description") or "").strip()
            lines.append(f"- **{title}** ({tag})" + (f" — {desc}" if desc else ""))
        lines.append("")

    cases = draft.get("test_cases") or []
    if cases:
        lines += ["## Test cases (BRAHL draft)", ""]
        for t in cases[:40]:
            tag = "auto" if t.get("automated") is not False else "manual"
            lines.append(f"- `{t.get('id') or ''}` {t.get('title') or ''} [{tag}]".strip())
        if len(cases) > 40:
            lines.append(f"- …and {len(cases) - 40} more")
        lines.append("")

    if plan_rows:
        lines += [
            "## yPAD plans (`y1Plans.csv`)",
            "",
            "| PlanId | PlanName | Run | Tags |",
            "| --- | --- | --- | --- |",
        ]
        for r in plan_rows[:80]:
            pid = (r.get("PlanId") or "").replace("|", "/")
            name = (r.get("PlanName") or "").replace("|", "/")
            run = (r.get("Run") or "").replace("|", "/")
            tags = (r.get("Tags") or "").replace("|", "/")
            lines.append(f"| {pid} | {name} | {run} | {tags} |")
        if len(plan_rows) > 80:
            lines.append("")
            lines.append(f"_Showing 80 of {len(plan_rows)} plans — open Test coverage for the full table._")
        lines.append("")

    if draft.get("run_how"):
        lines += ["## How to run", "", str(draft["run_how"]), ""]

    lines.append(
        f"_Source: `y/{suite_name}/{DOC_META['plan']['filename']}` (synthesized if the file was missing)._"
    )
    return "\n".join(lines)


def build_suite_doc(
    suite_name: str,
    doc_id: str,
    *,
    project: dict[str, Any] | None = None,
    persist_if_missing: bool = False,
) -> dict[str, Any]:
    if doc_id not in DOC_META:
        raise KeyError(doc_id)
    meta = DOC_META[doc_id]
    suite = get_suite_detail(suite_name)
    if not suite:
        raise FileNotFoundError(f"Suite not found: {suite_name}")

    path = _doc_path(suite_name, doc_id)
    source = "file"
    if path.is_file():
        markdown = path.read_text(encoding="utf-8")
    else:
        source = "synthesized"
        plan_rows = _ypad_plan_rows(suite_name)
        if doc_id == "strategy":
            markdown = _synthesize_strategy(
                suite_name, suite=suite, project=project, plan_rows=plan_rows
            )
        else:
            markdown = _synthesize_plan(
                suite_name, suite=suite, project=project, plan_rows=plan_rows
            )
        if persist_if_missing:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(markdown, encoding="utf-8")
            source = "file"

    return {
        **meta,
        "suite": suite_name,
        "path": f"y/{suite_name}/{meta['filename']}",
        "exists_on_disk": path.is_file(),
        "source": source,
        "synopsis": _synopsis(markdown),
        "markdown": markdown,
    }


def list_suite_docs(
    suite_name: str,
    *,
    project: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for doc_id in DOC_IDS:
        doc = build_suite_doc(suite_name, doc_id, project=project)
        # List payload omits full markdown to keep the strip light
        out.append({k: v for k, v in doc.items() if k != "markdown"})
    return out


def write_suite_docs_from_context(
    suite_name: str,
    *,
    project: dict[str, Any] | None = None,
    brahl_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write both .md files under y/<suite>/ from current context (+ optional plan)."""
    merged = dict(project or {})
    if brahl_plan:
        merged = {**merged, "brahl_plan_draft": brahl_plan}
    written: list[str] = []
    for doc_id in DOC_IDS:
        doc = build_suite_doc(suite_name, doc_id, project=merged, persist_if_missing=False)
        # Force rewrite from synthesis using latest plan context
        plan_rows = _ypad_plan_rows(suite_name)
        suite = get_suite_detail(suite_name) or {"name": suite_name}
        if doc_id == "strategy":
            md = _synthesize_strategy(suite_name, suite=suite, project=merged, plan_rows=plan_rows)
        else:
            md = _synthesize_plan(suite_name, suite=suite, project=merged, plan_rows=plan_rows)
        path = _doc_path(suite_name, doc_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md, encoding="utf-8")
        written.append(f"y/{suite_name}/{DOC_META[doc_id]['filename']}")
    return {"written": written}
