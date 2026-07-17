"""Scaffold y/<suite>/ with D1–D9 persona y3Designs and starter smoke plans.

Run standalone: python u/scaffold_app_ypad.py <suite_name> [app_url]
Used by qoa_web create_ypad_suite() when Creators add a challenge.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from _paths import KK_ROOT, FOXYIZ_ROOT

DATA_DIR = KK_ROOT / "Docs" / "test-user-data"
Y_DIR = FOXYIZ_ROOT / "y"
F_DIR = FOXYIZ_ROOT / "f"


def slug_suite_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (name or "").strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "project"


def load_personas() -> list[dict[str, str]]:
    """Load Docs/test-user-data personas; fall back to a single D1 column when missing."""
    idx_path = DATA_DIR / "index.json"
    if not idx_path.is_file():
        return [
            {
                "column": "D1",
                "id": "P1",
                "code": "P1",
                "name": "Default",
                "default_avatar": "client",
                "can_hitl": True,
                "can_client": True,
            }
        ]
    idx = json.loads(idx_path.read_text(encoding="utf-8"))
    out: list[dict[str, str]] = []
    for entry in idx.get("personas", []):
        p = json.loads((DATA_DIR / entry["file"]).read_text(encoding="utf-8"))
        out.append(
            {
                "column": entry["ypad_design_column"],
                "id": p["id"],
                "code": p["code"],
                "name": p["name"],
                "default_avatar": p.get("default_avatar", "client"),
                "can_hitl": "consultant" in (p.get("allowed_avatars") or []),
                "can_client": "client" in (p.get("allowed_avatars") or []),
            }
        )
    return out or [
        {
            "column": "D1",
            "id": "P1",
            "code": "P1",
            "name": "Default",
            "default_avatar": "client",
            "can_hitl": True,
            "can_client": True,
        }
    ]


def _col_map(fn) -> dict[str, str]:
    personas = load_personas()
    return {p["column"]: fn(p) for p in personas}


def _normalize_app_url(app_url: str) -> str:
    url = (app_url or "").strip()
    if url and not url.endswith("/"):
        url += "/"
    return url


def _route_urls(base: str) -> dict[str, str]:
    """Best-effort route hints from app URL (Creators fill in yDesigns)."""
    if not base:
        return {}
    parsed = urlparse(base)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return {
        "explore_url": f"{origin}/explore",
        "login_url": f"{origin}/login",
    }


def build_y3_designs_rows(app_url: str) -> list[dict[str, str]]:
    personas = load_personas()
    cols = [p["column"] for p in personas]
    base = _normalize_app_url(app_url)
    routes = _route_urls(base)
    rows: list[dict[str, str]] = []

    def add(typ: str, name: str, vals: dict[str, str]) -> None:
        rows.append({"Type": typ, "DataName": name, **{c: vals.get(c, "") for c in cols}})

    add("UI", "persona_id", _col_map(lambda p: p["id"]))
    add("UI", "persona_code", _col_map(lambda p: p["code"]))
    add("UI", "persona_name", _col_map(lambda p: p["name"]))
    add("UI", "default_avatar", _col_map(lambda p: p["default_avatar"]))
    add("UI", "can_switch_client", _col_map(lambda p: "Y" if p["can_client"] else "N"))
    add("UI", "can_switch_hitl", _col_map(lambda p: "Y" if p["can_hitl"] else "N"))
    add("UI", "login_email", {c: "" for c in cols})
    add("UI", "login_password", {c: "" for c in cols})

    shared_app: dict[str, str] = {
        "base_url": base,
        "body_locator": "css=body",
        "title_locator": "css=title",
        "h1_locator": "css=h1",
        "page_title_contains": "",
    }
    shared_app.update(routes)
    for key, val in shared_app.items():
        add("UI", key, {c: val for c in cols})

    return rows


def write_y3_designs(path: Path, app_url: str) -> None:
    personas = load_personas()
    cols = [p["column"] for p in personas]
    rows = build_y3_designs_rows(app_url)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Type", "DataName", *cols])
        w.writeheader()
        w.writerows(rows)


def _plan_prefix(suite: str) -> str:
    parts = re.split(r"[_-]+", suite)
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _annotate_plan_rows(plans: list[tuple], created_by: str) -> list[tuple]:
    """Append CreatedBy / CreatedAt to each plan row tuple — mirrors qoa_web's
    ypad_versions.annotate_plan_creator so every newly scaffolded plan carries
    provenance, whether written by the web app or this standalone script."""
    stamp = _now_iso()
    return [(*row, created_by or "", stamp) for row in plans]


def write_smoke_ypad(y_dir: Path, suite: str, app_url: str, *, created_by: str = "") -> None:
    prefix = _plan_prefix(suite)
    reuse = f"PReuse_{prefix}_OpenSite"
    landing = f"P{prefix}_Smoke_Landing"

    plans = [
        (reuse, f"Open browser and navigate to {suite}", "D1", "N", "Reuse", "site_loaded"),
        (landing, "Verify landing page loads", "D1", "Y", f"{suite};Smoke;Landing", "landing_ok"),
    ]

    actions = [
        (reuse, 1, "Open browser", "xUI", "xOpenBrowser", "edge", "", "", "y"),
        (reuse, 2, "Navigate to app", "xUI", "xNavigate", "base_url", "", "", "y"),
        (reuse, 3, "Verify body present", "xUI", "xGetText", "body_locator", "", "", "y"),
        (landing, 1, "Open site", "xReuse", reuse, "", "", "", "y"),
        (landing, 2, "Verify page body", "xUI", "xGetText", "body_locator", "", "", "y"),
    ]
    if app_url.strip():
        actions.append((landing, 3, "Verify page title", "xUI", "xGetTitle", "", "", "page_title_contains", "y"))

    with (y_dir / "y1Plans.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"])
        w.writerows(_annotate_plan_rows(plans, created_by))

    with (y_dir / "y2Actions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"])
        w.writerows(actions)


def _slug_plan_token(text: str, max_len: int = 28) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (text or "").strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return (slug or "Case")[:max_len]


def write_ypad_from_brahl_plan(
    y_dir: Path,
    suite: str,
    app_url: str,
    brahl_plan: dict[str, Any] | None,
    *,
    max_auto: int = 12,
    created_by: str = "",
) -> dict[str, Any]:
    """Materialize automated + Manual test_cases into y1/y2 white pads.

    Automated → Run=Y. Manual → Run=N with Manual tag (human coverage).
    Falls back to the fixed smoke landing plan when no automated cases exist.
    """
    cases = list((brahl_plan or {}).get("test_cases") or [])
    auto = [c for c in cases if c.get("automated") is not False][:max_auto]
    if not auto:
        write_smoke_ypad(y_dir, suite, app_url, created_by=created_by)
        return {"mode": "smoke", "automated_plans": 1, "skipped_manual": len(cases)}

    prefix = _plan_prefix(suite)
    reuse = f"PReuse_{prefix}_OpenSite"
    plans: list[tuple] = [
        (reuse, f"Open browser and navigate to {suite}", "D1", "N", "Reuse", "site_loaded"),
    ]
    actions: list[tuple] = [
        (reuse, 1, "Open browser", "xUI", "xOpenBrowser", "edge", "", "", "y"),
        (reuse, 2, "Navigate to app", "xUI", "xNavigate", "base_url", "", "", "y"),
        (reuse, 3, "Verify body present", "xUI", "xGetText", "body_locator", "", "", "y"),
    ]
    used_ids: set[str] = {reuse}

    for i, case in enumerate(auto, start=1):
        title = (case.get("title") or f"Case {i}").strip()
        tid = (case.get("id") or f"T{i}").strip()
        token = _slug_plan_token(f"{tid}_{title}")
        plan_id = f"P{prefix}_{token}"
        if plan_id in used_ids:
            plan_id = f"P{prefix}_T{i}_{token}"[:60]
        used_ids.add(plan_id)
        plans.append(
            (
                plan_id,
                title[:120],
                "D1",
                "Y",
                f"{suite};Smoke;BRAHL;{tid}",
                f"case_{i}_ok",
            )
        )
        actions.append((plan_id, 1, "Open site", "xReuse", reuse, "", "", "", "y"))
        # Route hint from case title — use design URLs when keywords match
        title_l = title.lower()
        nav_data = "base_url"
        if any(k in title_l for k in ("login", "sign in", "auth", "session")):
            nav_data = "login_url"
        elif any(k in title_l for k in ("explore", "discover", "browse", "search")):
            nav_data = "explore_url"
        if nav_data != "base_url":
            actions.append((plan_id, 2, f"Navigate ({nav_data})", "xUI", "xNavigate", nav_data, "", "", "y"))
            actions.append((plan_id, 3, f"Verify: {title[:80]}", "xUI", "xGetText", "body_locator", "", "", "y"))
            step = 4
        else:
            actions.append((plan_id, 2, f"Verify: {title[:80]}", "xUI", "xGetText", "body_locator", "", "", "y"))
            step = 3
        if app_url.strip():
            actions.append((plan_id, step, "Verify page title", "xUI", "xGetTitle", "", "", "page_title_contains", "y"))

    # Manual cases → Run=N + Manual tag (human coverage; not executed by FoXYiZ Run=Y)
    manual_cases = [c for c in cases if c.get("automated") is False]
    for i, case in enumerate(manual_cases, start=1):
        title = (case.get("title") or f"Manual {i}").strip()
        tid = (case.get("id") or f"M{i}").strip()
        token = _slug_plan_token(f"{tid}_{title}")
        plan_id = f"P{prefix}_Man_{token}"
        if plan_id in used_ids:
            plan_id = f"P{prefix}_Man_T{i}_{token}"[:60]
        used_ids.add(plan_id)
        plans.append(
            (
                plan_id,
                title[:120],
                "D1",
                "N",
                f"{suite};Manual;{tid}",
                f"manual_{i}_ok",
            )
        )
        actions.append(
            (
                plan_id,
                1,
                f"Manual: {title[:80]}",
                "xUI",
                "xGetText",
                "body_locator",
                "",
                "",
                "n",
            )
        )

    with (y_dir / "y1Plans.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"])
        w.writerows(_annotate_plan_rows(plans, created_by))

    with (y_dir / "y2Actions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"])
        w.writerows(actions)

    manual = len(manual_cases)
    return {
        "mode": "brahl_plan",
        "automated_plans": len(auto),
        "manual_plans": manual,
        "skipped_manual": 0,
        "reuse": reuse,
    }


def write_fstart(suite: str, tag: str | None = None) -> Path:
    safe = slug_suite_name(suite)
    cfg = {
        "configs": [f"y/{safe}/{safe}.json"],
        "thread_count": 1,
        "timeout": 15,
        "headless": True,
        "debug": False,
        "tags": [tag or "Smoke"],
    }
    fstart_dir = F_DIR / "fStart"
    fstart_dir.mkdir(parents=True, exist_ok=True)
    path = fstart_dir / f"{safe}_smoke.json"
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def materialize_brahl_plan_suite(
    suite_name: str,
    app_url: str = "",
    brahl_plan: dict[str, Any] | None = None,
    *,
    created_by: str = "",
) -> dict[str, Any]:
    """Rewrite y1/y2 for an existing suite from a BRAHL plan (keeps y3Designs)."""
    safe = slug_suite_name(suite_name)
    y_dir = Y_DIR / safe
    if not y_dir.is_dir():
        raise FileNotFoundError(f"Suite folder missing: y/{safe}")
    if not (y_dir / "y3Designs.csv").is_file():
        write_y3_designs(y_dir / "y3Designs.csv", app_url)
    meta = write_ypad_from_brahl_plan(y_dir, safe, app_url, brahl_plan, created_by=created_by)
    meta["suite"] = safe
    meta["path"] = f"y/{safe}/{safe}.json"
    return meta


def write_app_ypad_suite(
    name: str,
    app_url: str = "",
    description: str = "",
    brahl_plan: dict[str, Any] | None = None,
    *,
    created_by: str = "",
) -> dict[str, Any]:
    """Create y/<name>/ with persona y3Designs, plan-driven or smoke yPAD, suite JSON, and fStart."""
    safe = slug_suite_name(name)
    y_dir = Y_DIR / safe
    config_path = y_dir / f"{safe}.json"
    if config_path.is_file():
        raise ValueError(f"Project already exists: {safe}")

    y_dir.mkdir(parents=True, exist_ok=True)
    rel_config = f"y/{safe}/{safe}.json"
    config = {
        "input_files": {
            "yPlans": [f"y/{safe}/y1Plans.csv"],
            "yActions": [f"y/{safe}/y2Actions.csv"],
            "yDesigns": [f"y/{safe}/y3Designs.csv"],
        },
        "name": safe,
        "description": description or f"BRAHL project {safe}",
        "version": "1.0.0",
        "url": app_url or "",
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    write_y3_designs(y_dir / "y3Designs.csv", app_url)
    pad_meta = write_ypad_from_brahl_plan(y_dir, safe, app_url, brahl_plan, created_by=created_by)
    fstart = write_fstart(safe)

    personas = load_personas()
    return {
        "path": rel_config,
        "name": safe,
        "url": app_url,
        "description": description,
        "fstart_smoke": str(fstart.relative_to(FOXYIZ_ROOT)).replace("\\", "/"),
        "persona_columns": len(personas),
        "ypad": pad_meta,
    }


def upgrade_y3_designs_to_personas(path: Path, app_url: str) -> None:
    """Expand single-D1 y3Designs to full D1–D9 template, preserving existing D1 values."""
    if not path.is_file():
        return
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        old_rows = list(reader)
        old_headers = reader.fieldnames or []

    d1_values: dict[str, str] = {}
    for row in old_rows:
        d1_values[row.get("DataName", "")] = row.get("D1", "")

    personas = load_personas()
    cols = [p["column"] for p in personas]
    template = {r["DataName"]: r for r in build_y3_designs_rows(app_url)}

    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in old_rows:
        name = row.get("DataName", "")
        seen.add(name)
        out = {"Type": row.get("Type", "UI"), "DataName": name}
        for c in cols:
            if c == "D1":
                out[c] = d1_values.get(name, row.get("D1", ""))
            elif name in template:
                out[c] = template[name].get(c, d1_values.get(name, ""))
            else:
                out[c] = d1_values.get(name, "")
        merged.append(out)

    for name, tmpl in template.items():
        if name in seen:
            continue
        merged.append(tmpl)

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["Type", "DataName", *cols])
        w.writeheader()
        w.writerows(merged)


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: python u/scaffold_app_ypad.py <suite_name> [app_url]")
        sys.exit(1)
    name = argv[0]
    app_url = argv[1] if len(argv) > 1 else ""
    result = write_app_ypad_suite(name, app_url)
    print(f"Scaffolded {result['name']} ({result['persona_columns']} persona columns)")
    print(f"  config: {result['path']}")
    print(f"  smoke:  {result['fstart_smoke']}")


if __name__ == "__main__":
    main()
