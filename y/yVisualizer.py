#!/usr/bin/env python3
"""
yVisualizer — Interactive HTML visualization of FoXYiZ yPAD workflows (plans, actions, designs).

Resolves workflow JSON files under the y/ folder, loads merged CSVs referenced by
input_files (yPlans, yActions, yDesigns), and writes a single report with search,
workflow filter, clickable plan rows, design chips, lazy Mermaid diagrams, and a
slide-out explorer panel.

Usage (from Demo-main, where paths like y/FApp/... resolve):
  python y/yVisualizer.py
  python y/yVisualizer.py --base . --out y/y_visualization.html
  python y/yVisualizer.py --config y/QAonAIR.json

Requires: Python 3.9+ (stdlib only; pathlib.relative_to).
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys and strip cell values
            clean = {k.strip(): (v.strip() if v is not None else "") for k, v in row.items() if k}
            if any(clean.values()) or any(k for k in clean):
                rows.append(clean)
    return rows


def _discover_workflow_configs(y_dir: Path) -> list[Path]:
    """Find *.json under y/ that look like FoXYiZ workflow configs."""
    out: list[Path] = []
    for p in sorted(y_dir.rglob("*.json")):
        try:
            data = _read_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict) and "input_files" in data:
            inf = data.get("input_files")
            if isinstance(inf, dict) and inf.get("yPlans"):
                out.append(p)
    return out


def _resolve_path(base: Path, rel: str) -> Path:
    rel = rel.replace("\\", "/").lstrip("/")
    return (base / rel).resolve()


def _merge_csvs(base: Path, rel_paths: Iterable[str]) -> tuple[list[dict[str, str]], list[str]]:
    merged: list[dict[str, str]] = []
    warnings: list[str] = []
    for rel in rel_paths:
        p = _resolve_path(base, rel)
        if not p.is_file():
            warnings.append(f"Missing file (skipped): {rel}")
            continue
        merged.extend(_read_csv_rows(p))
    return merged, warnings


def _escape_pre(text: str) -> str:
    """Escape minimal for <pre> text (do not use full html.escape — breaks Mermaid)."""
    return text.replace("&", "&amp;").replace("<", "&lt;")


def _mermaid_safe(s: str, max_len: int = 80) -> str:
    s = re.sub(r"[\r\n]+", " ", s)
    s = s.replace('"', "'")
    if len(s) > max_len:
        s = s[: max_len - 1] + "…"
    return s


def _extract_var_refs(text: str, design_names: set[str]) -> list[str]:
    if not text or text.lower() in ("nan", "none"):
        return []
    found: list[str] = []
    for name in sorted(design_names, key=len, reverse=True):
        if name and name in text:
            found.append(name)
    return found


def _step_sort_key(row: dict[str, str]) -> float:
    try:
        return float(str(row.get("StepId", "0")) or 0)
    except ValueError:
        return 0.0


def _safe_dom_id(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", s)[:120]


def _build_mermaid_for_plan(plan_id: str, steps: list[dict[str, str]]) -> str:
    """Flowchart LR for one plan's steps."""
    lines = ["flowchart LR"]
    for i, row in enumerate(sorted(steps, key=_step_sort_key)):
        sid = row.get("StepId", str(i + 1))
        info = _mermaid_safe(row.get("StepInfo", "") or f"Step {sid}")
        atype = _mermaid_safe(row.get("ActionType", ""))
        aname = _mermaid_safe(row.get("ActionName", ""))
        label = f"{sid}: {info}<br/>{atype} → {aname}"
        node_id = f"S{i}"
        lines.append(f'    {node_id}["{label}"]')
        if i > 0:
            lines.append(f"    S{i - 1} --> {node_id}")
    return "\n".join(lines) if len(lines) > 1 else ""


def _explorer_script() -> str:
    """Vanilla JS: search, plan navigation, lazy Mermaid, explorer panel."""
    return """
<script type="module">
const MERMAID_SRC = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
let mermaidSingleton = null;
async function getMermaid() {
  if (!mermaidSingleton) {
    const m = await import(MERMAID_SRC);
    m.default.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "loose" });
    mermaidSingleton = m.default;
  }
  return mermaidSingleton;
}
function norm(s) { return (s || "").toLowerCase().trim(); }
function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}
function applySearch(q) {
  const term = norm(q);
  document.querySelectorAll("section.wf").forEach((sec) => {
    let show = !term || norm(sec.innerText).includes(term);
    if (!show) {
      sec.querySelectorAll("[data-search-text]").forEach((el) => {
        if (norm(el.dataset.searchText || "").includes(term)) show = true;
      });
    }
    sec.classList.toggle("wf-hidden", !show);
  });
}
function applyWorkflowFilter(slug) {
  document.querySelectorAll("section.wf").forEach((sec) => {
    const match = !slug || slug === "__all__" || sec.dataset.wfSlug === slug;
    sec.classList.toggle("wf-filtered-out", !match);
  });
}
document.addEventListener("DOMContentLoaded", () => {
  const search = document.getElementById("yviz-search");
  const wfSel = document.getElementById("yviz-wf-filter");
  const explorer = document.getElementById("yviz-explorer");
  const explorerBody = document.getElementById("yviz-explorer-body");
  const explorerTitle = document.getElementById("yviz-explorer-title");
  const closeEx = document.getElementById("yviz-explorer-close");

  if (search) {
    search.addEventListener("input", () => applySearch(search.value));
    document.addEventListener("keydown", (e) => {
      if (e.key === "/" && document.activeElement === document.body) {
        e.preventDefault();
        search.focus();
      }
    });
  }
  if (wfSel) wfSel.addEventListener("change", () => applyWorkflowFilter(wfSel.value));

  document.querySelectorAll(".yviz-expand-wf").forEach((btn) => {
    btn.addEventListener("click", () => {
      const slug = btn.dataset.wfSlug;
      const sec = document.querySelector('section.wf[data-wf-slug="' + slug + '"]');
      if (!sec) return;
      const doOpen = btn.classList.contains("yviz-do-expand");
      sec.querySelectorAll("details.plan").forEach((d) => { d.open = doOpen; });
    });
  });

  document.getElementById("yviz-expand-all")?.addEventListener("click", () => {
    document.querySelectorAll("details.plan").forEach((d) => { d.open = true; });
  });
  document.getElementById("yviz-collapse-all")?.addEventListener("click", () => {
    document.querySelectorAll("details.plan").forEach((d) => { d.open = false; });
  });

  function openExplorer(html, title) {
    if (!explorer || !explorerBody) return;
    if (explorerTitle) explorerTitle.textContent = title || "Plan";
    explorerBody.innerHTML = html;
    explorer.classList.add("open");
    explorer.setAttribute("aria-hidden", "false");
  }
  closeEx?.addEventListener("click", () => {
    explorer?.classList.remove("open");
    explorer?.setAttribute("aria-hidden", "true");
  });

  document.querySelectorAll("tr.plan-row").forEach((tr) => {
    tr.addEventListener("click", () => {
      const tid = tr.dataset.planDetailId;
      const det = tid ? document.getElementById(tid) : null;
      if (det) {
        det.open = true;
        det.scrollIntoView({ behavior: "smooth", block: "nearest" });
        det.classList.add("yviz-flash");
        setTimeout(() => det.classList.remove("yviz-flash"), 1600);
      }
      const cells = tr.querySelectorAll("td");
      const meta = Array.from(cells).map((td) => td.textContent).join(" · ");
      const pid = tr.dataset.planId || "";
      openExplorer("<p class='explorer-meta'>" + escapeHtml(meta) + "</p><p><small>Steps opened below. Use <strong>Diagram</strong> for Mermaid flow.</small></p>", pid);
    });
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        tr.click();
      }
    });
  });

  document.querySelectorAll("details.plan").forEach((det) => {
    det.addEventListener("toggle", async () => {
      if (!det.open) return;
      const pre = det.querySelector("pre.mermaid");
      if (!pre || pre.dataset.mermaidDone) return;
      pre.dataset.mermaidDone = "1";
      const mm = await getMermaid();
      await mm.run({ nodes: [pre] });
    });
  });

  document.querySelectorAll(".design-pill").forEach((pill) => {
    pill.addEventListener("click", (e) => {
      e.preventDefault();
      const name = pill.dataset.varName || "";
      if (search) {
        search.value = name;
        applySearch(name);
      }
    });
  });
});
</script>
"""


def _html_report(
    base: Path,
    workflows: list[tuple[str, dict[str, Any], list[str]]],
) -> str:
    """
    workflows: list of (workflow_name, payload_dict, merge_warnings)
    payload: plans, actions, designs, design_names, var_usage, path_warnings
    """
    parts: list[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append('<html lang="en"><head><meta charset="utf-8">')
    parts.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append("<title>yPAD Visualizer — FoXYiZ workflows</title>")
    parts.append(
        "<style>"
        ":root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --accent:#38bdf8; --ok:#22c55e; --border:#334155; }"
        "body { font-family: ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--text); margin: 0; line-height: 1.5; }"
        "header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); background: var(--panel); position: sticky; top: 0; z-index: 20; }"
        "header h1 { margin: 0 0 0.25rem 0; font-size: 1.35rem; }"
        "header p { margin: 0; color: var(--muted); font-size: 0.9rem; }"
        ".toolbar { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; padding: 0.65rem 1.5rem; background: #0c1222; border-bottom: 1px solid var(--border); position: sticky; top: 72px; z-index: 15; }"
        ".toolbar input[type=search] { flex: 1; min-width: 200px; max-width: 420px; padding: 0.45rem 0.75rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); }"
        ".toolbar select { padding: 0.45rem 0.6rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); }"
        ".toolbar button { padding: 0.45rem 0.75rem; border-radius: 8px; border: 1px solid var(--border); background: var(--panel); color: var(--text); cursor: pointer; font-size: 0.85rem; }"
        ".toolbar button:hover { border-color: var(--accent); color: var(--accent); }"
        "nav.toc { padding: 1rem 1.5rem; max-width: 280px; float: left; position: sticky; top: 130px; align-self: start; max-height: calc(100vh - 140px); overflow: auto; }"
        "nav.toc a { display: block; color: var(--accent); text-decoration: none; padding: 0.25rem 0; font-size: 0.9rem; }"
        "nav.toc a:hover { text-decoration: underline; }"
        "main { margin-left: 300px; padding: 1.5rem; padding-bottom: 4rem; max-width: 1200px; }"
        "@media (max-width: 900px) { nav.toc { float: none; max-width: none; position: relative; top: 0; } main { margin-left: 0; } .toolbar { top: 0; position: relative; } }"
        "section.wf { margin-bottom: 3rem; padding-bottom: 2rem; border-bottom: 1px solid var(--border); }"
        "section.wf.wf-hidden, section.wf.wf-filtered-out { display: none !important; }"
        "section.wf h2 { font-size: 1.15rem; margin-top: 0; color: var(--accent); }"
        ".wf-tools { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0.5rem 0 1rem; }"
        ".wf-tools button { font-size: 0.8rem; padding: 0.25rem 0.5rem; border-radius: 6px; border: 1px solid var(--border); background: #0c1222; color: var(--text); cursor: pointer; }"
        ".wf-tools button:hover { border-color: var(--accent); }"
        ".design-pills { display: flex; flex-wrap: wrap; gap: 0.35rem; margin: 0.5rem 0 1rem; }"
        ".design-pill { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 999px; border: 1px solid var(--border); background: #0c1222; color: var(--accent); cursor: pointer; }"
        ".design-pill:hover { background: var(--panel); }"
        ".stats { display: flex; flex-wrap: wrap; gap: 0.75rem; margin: 1rem 0; }"
        ".stat { background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; min-width: 120px; }"
        ".stat .n { font-size: 1.5rem; font-weight: 700; }"
        ".stat .l { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; }"
        "table.data { width: 100%; border-collapse: collapse; font-size: 0.85rem; margin: 1rem 0; }"
        "table.data th, table.data td { border: 1px solid var(--border); padding: 0.4rem 0.6rem; text-align: left; vertical-align: top; }"
        "table.data th { background: var(--panel); color: var(--muted); font-weight: 600; }"
        "table.data tr:nth-child(even) { background: rgba(30,41,59,0.5); }"
        "tr.plan-row { cursor: pointer; transition: background 0.15s; }"
        "tr.plan-row:hover, tr.plan-row:focus { background: rgba(56,189,248,0.12); outline: none; }"
        "tr.plan-row:focus-visible { box-shadow: inset 0 0 0 2px var(--accent); }"
        "details.plan { margin: 0.5rem 0; border: 1px solid var(--border); border-radius: 8px; background: var(--panel); }"
        "details.plan summary { padding: 0.6rem 1rem; cursor: pointer; font-weight: 600; list-style: none; }"
        "details.plan summary::-webkit-details-marker { display: none; }"
        "details.plan .inner { padding: 0 1rem 1rem; }"
        "details.plan.yviz-flash { box-shadow: 0 0 0 2px var(--accent); }"
        ".mermaid { background: #fff; border-radius: 8px; padding: 1rem; margin: 0.5rem 0; min-height: 2rem; }"
        ".warn { color: #fbbf24; font-size: 0.85rem; }"
        ".tag { display: inline-block; background: #334155; padding: 0.1rem 0.45rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.25rem; }"
        "code { font-family: ui-monospace, monospace; font-size: 0.8rem; }"
        ".yviz-explorer { position: fixed; right: 0; top: 0; width: min(400px, 100vw); height: 100vh; background: var(--panel); border-left: 1px solid var(--border); z-index: 200; transform: translateX(100%); transition: transform 0.22s ease; display: flex; flex-direction: column; box-shadow: -4px 0 24px rgba(0,0,0,0.35); }"
        ".yviz-explorer.open { transform: translateX(0); }"
        ".yviz-explorer-head { display: flex; justify-content: space-between; align-items: center; padding: 1rem; border-bottom: 1px solid var(--border); }"
        ".yviz-explorer-head h3 { margin: 0; font-size: 1rem; word-break: break-all; }"
        "#yviz-explorer-close { font-size: 1.5rem; line-height: 1; border: none; background: none; color: var(--muted); cursor: pointer; padding: 0 0.25rem; }"
        "#yviz-explorer-close:hover { color: var(--text); }"
        "#yviz-explorer-body { padding: 1rem; overflow: auto; flex: 1; font-size: 0.9rem; }"
        ".explorer-meta { color: var(--muted); font-size: 0.85rem; word-break: break-word; }"
        "</style>"
    )
    parts.append("</head><body>")
    parts.append("<header>")
    parts.append("<h1>yPAD Visualizer</h1>")
    parts.append(f"<p>Base: <code>{html.escape(str(base))}</code> — Click a <strong>plan row</strong> to jump to steps; use <strong>search</strong> and <strong>design chips</strong> to explore.</p>")
    parts.append("</header>")

    parts.append('<div class="toolbar" id="yviz-toolbar">')
    parts.append('<input type="search" id="yviz-search" placeholder="Filter everything… (press / to focus)" autocomplete="off" />')
    parts.append('<select id="yviz-wf-filter" title="Show one workflow">')
    parts.append('<option value="__all__">All workflows</option>')
    for name, _, _ in workflows:
        wf_slug = _safe_dom_id(name)
        parts.append(f'<option value="{html.escape(wf_slug)}">{html.escape(name)}</option>')
    parts.append("</select>")
    parts.append('<button type="button" id="yviz-expand-all" title="Open all plan details">Expand all</button>')
    parts.append('<button type="button" id="yviz-collapse-all" title="Close all plan details">Collapse all</button>')
    parts.append("</div>")

    parts.append('<nav class="toc"><strong>Workflows</strong>')
    for name, _, _ in workflows:
        aid = re.sub(r"[^\w\-]", "-", name)
        parts.append(f'<a href="#wf-{aid}">{html.escape(name)}</a>')
    parts.append("</nav>")

    parts.append("<main>")
    for name, payload, merge_warnings in workflows:
        aid = re.sub(r"[^\w\-]", "-", name)
        wf_slug = _safe_dom_id(name)
        plans = payload["plans"]
        actions = payload["actions"]
        designs = payload["designs"]
        design_names: set[str] = payload["design_names"]
        var_usage: dict[str, list[str]] = payload["var_usage"]
        path_warnings = payload.get("path_warnings", [])

        parts.append(f'<section class="wf" id="wf-{html.escape(aid, quote=True)}" data-wf-slug="{html.escape(wf_slug)}">')
        parts.append(f"<h2>{html.escape(name)}</h2>")
        parts.append('<div class="wf-tools">')
        parts.append(
            f'<button type="button" class="yviz-expand-wf yviz-do-expand" data-wf-slug="{html.escape(wf_slug)}">Expand plans in this workflow</button>'
        )
        parts.append(
            f'<button type="button" class="yviz-expand-wf" data-wf-slug="{html.escape(wf_slug)}">Collapse plans</button>'
        )
        parts.append("</div>")
        if var_usage:
            parts.append('<div class="design-pills" aria-label="Jump to design variable in search">')
            for vn in sorted(var_usage.keys(), key=str.lower)[:36]:
                parts.append(
                    f'<button type="button" class="design-pill" data-var-name="{html.escape(vn)}" title="Search for {html.escape(vn)}">#{html.escape(vn)}</button>'
                )
            parts.append("</div>")

        all_warns = merge_warnings + path_warnings
        if all_warns:
            parts.append('<div class="warn">')
            for w in all_warns:
                parts.append(f"⚠ {html.escape(w)}<br/>")
            parts.append("</div>")

        run_y = sum(1 for p in plans if (p.get("Run") or "").upper().startswith("Y"))
        parts.append('<div class="stats">')
        parts.append(f'<div class="stat"><div class="n">{len(plans)}</div><div class="l">Plans</div></div>')
        parts.append(f'<div class="stat"><div class="n">{run_y}</div><div class="l">Run = Y</div></div>')
        parts.append(f'<div class="stat"><div class="n">{len(actions)}</div><div class="l">Action rows</div></div>')
        parts.append(f'<div class="stat"><div class="n">{len(designs)}</div><div class="l">Design rows</div></div>')
        parts.append("</div>")

        # Plans table
        parts.append("<h3>Plans (y1Plans)</h3>")
        plan_keys = ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output"]
        pk = [k for k in plan_keys if plans and k in plans[0]]
        if plans:
            for p in plans:
                for k in p.keys():
                    if k not in pk:
                        pk.append(k)
        parts.append('<table class="data"><thead><tr>')
        for k in pk:
            parts.append(f"<th>{html.escape(k)}</th>")
        parts.append("</tr></thead><tbody>")
        for p in plans:
            pid = p.get("PlanId", "")
            plan_detail_id = f"plan-{wf_slug}-{_safe_dom_id(pid)}"
            search_blob = " ".join(str(p.get(x, "")) for x in pk)
            parts.append(
                f'<tr class="plan-row" data-wf-slug="{html.escape(wf_slug)}" data-plan-id="{html.escape(pid)}" '
                f'data-plan-detail-id="{html.escape(plan_detail_id)}" data-search-text="{html.escape(search_blob)}" '
                f'tabindex="0" role="button" title="Open steps & diagram for this plan">'
            )
            for k in pk:
                v = p.get(k, "")
                parts.append(f"<td>{html.escape(v)}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

        # Designs table (truncate long cells)
        parts.append("<h3>Designs (y3Designs)</h3>")
        if not designs:
            parts.append("<p class='warn'>No design rows loaded.</p>")
        else:
            dkeys = list(designs[0].keys())
            parts.append('<table class="data"><thead><tr>')
            for k in dkeys:
                parts.append(f"<th>{html.escape(k)}</th>")
            parts.append("</tr></thead><tbody>")
            for d in designs:
                ds = " ".join(str(d.get(x, "")) for x in dkeys)
                parts.append(f'<tr data-search-text="{html.escape(ds)}">')
                for k in dkeys:
                    v = d.get(k, "")
                    if len(v) > 120:
                        v = v[:117] + "…"
                    parts.append(f"<td><code>{html.escape(v)}</code></td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")

        # Variable usage
        parts.append("<h3>Design variables referenced in actions</h3>")
        if var_usage:
            parts.append('<table class="data"><thead><tr><th>DataName</th><th>Used in plans (steps)</th></tr></thead><tbody>')
            for vn in sorted(var_usage.keys(), key=str.lower):
                refs = var_usage[vn][:40]
                extra = f" (+{len(var_usage[vn]) - 40} more)" if len(var_usage[vn]) > 40 else ""
                ref_s = ", ".join(refs) + extra
                vs = vn + " " + ref_s
                parts.append(
                    f'<tr data-search-text="{html.escape(vs)}"><td><code>{html.escape(vn)}</code></td>'
                    f"<td>{html.escape(ref_s)}</td></tr>"
                )
            parts.append("</tbody></table>")
        else:
            parts.append("<p class='warn'>No design variable names detected in action inputs (or no designs).</p>")

        # Per-plan Mermaid
        parts.append("<h3>Action flow per plan (y2Actions)</h3>")
        by_plan: dict[str, list[dict[str, str]]] = defaultdict(list)
        for a in actions:
            pid = a.get("PlanId", "")
            if pid:
                by_plan[pid].append(a)

        plan_ids_sorted = sorted(by_plan.keys(), key=str.lower)
        for pid in plan_ids_sorted:
            steps = by_plan[pid]
            pmeta = next((x for x in plans if x.get("PlanId") == pid), {})
            pname = pmeta.get("PlanName", "")
            run = pmeta.get("Run", "")
            tags = pmeta.get("Tags", "")
            plan_detail_id = f"plan-{wf_slug}-{_safe_dom_id(pid)}"
            step_blob = " ".join(f"{s.get('StepInfo','')} {s.get('ActionName','')} {s.get('Input','')}" for s in steps)
            search_blob = f"{pid} {pname} {tags} {step_blob}"
            mm = _build_mermaid_for_plan(pid, steps)
            parts.append(
                f'<details class="plan" id="{html.escape(plan_detail_id)}" data-plan-id="{html.escape(pid)}" '
                f'data-search-text="{html.escape(search_blob)}">'
            )
            parts.append("<summary>")
            parts.append(f"<code>{html.escape(pid)}</code>")
            if pname:
                parts.append(f" — {html.escape(pname)}")
            parts.append(f' <span class="tag">Run: {html.escape(run or "?")}</span>')
            if tags:
                parts.append(f' <span class="tag">{html.escape(tags)}</span>')
            parts.append("</summary>")
            parts.append('<div class="inner">')
            step_cols_pref = ["StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"]
            sc = [c for c in step_cols_pref if steps and c in steps[0]]
            for s in steps:
                for k in s.keys():
                    if k not in sc:
                        sc.append(k)
            parts.append('<table class="data"><thead><tr>')
            for c in sc:
                parts.append(f"<th>{html.escape(c)}</th>")
            parts.append("</tr></thead><tbody>")
            for s in sorted(steps, key=_step_sort_key):
                step_search = " ".join(str(s.get(c, "")) for c in sc)
                parts.append(f'<tr data-search-text="{html.escape(step_search)}">')
                for c in sc:
                    v = s.get(c, "")
                    if len(v) > 100:
                        v = v[:97] + "…"
                    parts.append(f"<td>{html.escape(v)}</td>")
                parts.append("</tr>")
            parts.append("</tbody></table>")
            if mm:
                mid = re.sub(r"[^\w]", "_", pid)[:60]
                parts.append(f'<pre class="mermaid" id="mm-{html.escape(mid)}">\n{_escape_pre(mm)}\n</pre>')
            parts.append("</div></details>")

        parts.append("</section>")

    parts.append("</main>")
    parts.append(
        '<aside id="yviz-explorer" class="yviz-explorer" aria-hidden="true">'
        '<div class="yviz-explorer-head">'
        '<h3 id="yviz-explorer-title">Plan</h3>'
        '<button type="button" id="yviz-explorer-close" aria-label="Close panel">×</button>'
        "</div>"
        '<div id="yviz-explorer-body"></div>'
        "</aside>"
    )
    parts.append(_explorer_script())
    parts.append("</body></html>")
    return "\n".join(parts)


def _process_workflow(base: Path, config_path: Path) -> tuple[str, dict[str, Any], list[str]]:
    name = config_path.stem
    data = _read_json(config_path)
    inf = data.get("input_files", {})
    merge_warnings: list[str] = []

    plans, w1 = _merge_csvs(base, inf.get("yPlans") or [])
    actions, w2 = _merge_csvs(base, inf.get("yActions") or [])
    designs, w3 = _merge_csvs(base, inf.get("yDesigns") or [])
    merge_warnings.extend(w1 + w2 + w3)

    design_names = {d.get("DataName", "").strip() for d in designs if d.get("DataName")}
    design_names.discard("")

    var_usage: dict[str, list[str]] = defaultdict(list)
    for a in actions:
        pid = a.get("PlanId", "")
        sid = a.get("StepId", "")
        for field in ("Input", "Output", "Expected"):
            text = a.get(field, "")
            for vn in _extract_var_refs(text, design_names):
                key = f"{pid} #{sid}" if pid else f"#{sid}"
                ref = f"{key} ({field})"
                if ref not in var_usage[vn]:
                    var_usage[vn].append(ref)

    payload = {
        "plans": plans,
        "actions": actions,
        "designs": designs,
        "design_names": design_names,
        "var_usage": dict(var_usage),
        "path_warnings": [],
    }
    return name, payload, merge_warnings


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_base = script_dir.parent

    ap = argparse.ArgumentParser(description="Visualize FoXYiZ yPAD workflows (plans, actions, designs).")
    ap.add_argument(
        "--base",
        type=Path,
        default=default_base,
        help="Directory where paths like y/... resolve (default: parent of y/ folder).",
    )
    ap.add_argument(
        "--y-dir",
        type=Path,
        default=None,
        help="Explicit y folder (default: --base / y).",
    )
    ap.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Single workflow JSON (e.g. y/FApp.json). Default: all *.json workflows in y/.",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output HTML path (default: --base / y / y_visualization.html).",
    )
    ap.add_argument("--list", action="store_true", help="List discovered workflows and exit.")
    args = ap.parse_args()

    base = args.base.resolve()
    y_dir = (args.y_dir or (base / "y")).resolve()

    if not y_dir.is_dir():
        raise SystemExit(f"y folder not found: {y_dir}")

    if args.config:
        configs = [args.config.resolve()]
        for c in configs:
            if not c.is_file():
                raise SystemExit(f"Config not found: {c}")
    else:
        configs = _discover_workflow_configs(y_dir)

    if args.list:
        print(f"Base: {base}")
        print(f"y dir: {y_dir}")
        for c in configs:
            try:
                disp = c.relative_to(base)
            except ValueError:
                disp = c
            print(f"  - {disp}")
        return

    if not configs:
        raise SystemExit(f"No workflow JSON files found in {y_dir} (expected *.json with input_files.yPlans).")

    workflows: list[tuple[str, dict[str, Any], list[str]]] = []
    for cfg in configs:
        rel_base = base
        # Config paths in JSON are relative to base (Demo-main), not y/
        name, payload, mw = _process_workflow(rel_base, cfg)
        workflows.append((name, payload, mw))

    out = args.out or (base / "y" / "y_visualization.html")
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    html_doc = _html_report(base, workflows)
    out.write_text(html_doc, encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Open in browser: file:///{str(out).replace(chr(92), '/')}")


if __name__ == "__main__":
    main()
