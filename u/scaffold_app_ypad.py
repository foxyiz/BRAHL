"""Scaffold y/<suite>/ with D1–D9 persona y3Designs and starter smoke plans.

Run standalone: python u/scaffold_app_ypad.py <suite_name> [app_url]
Used by qoa_web create_ypad_suite() when Creators add a challenge.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from _paths import KK_ROOT

DATA_DIR = KK_ROOT / "Docs" / "test-user-data"
Y_DIR = KK_ROOT / "y"
F_DIR = KK_ROOT / "f"


def slug_suite_name(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (name or "").strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "project"


def load_personas() -> list[dict[str, str]]:
    idx = json.loads((DATA_DIR / "index.json").read_text(encoding="utf-8"))
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
    return out


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


def write_smoke_ypad(y_dir: Path, suite: str, app_url: str) -> None:
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
        w.writerow(["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output"])
        w.writerows(plans)

    with (y_dir / "y2Actions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"])
        w.writerows(actions)


def write_fstart(suite: str, tag: str | None = None) -> Path:
    safe = slug_suite_name(suite)
    tag = tag or "".join(p.capitalize() for p in safe.split("_"))
    cfg = {
        "configs": [f"y/{safe}/{safe}.json"],
        "thread_count": 1,
        "timeout": 15,
        "headless": False,
        "debug": False,
        "tags": [tag],
    }
    path = F_DIR / f"fStart_{safe}_smoke.json"
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def write_app_ypad_suite(name: str, app_url: str = "", description: str = "") -> dict[str, Any]:
    """Create y/<name>/ with persona y3Designs, smoke yPAD, suite JSON, and fStart config."""
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
    write_smoke_ypad(y_dir, safe, app_url)
    fstart = write_fstart(safe)

    personas = load_personas()
    return {
        "path": rel_config,
        "name": safe,
        "url": app_url,
        "description": description,
        "fstart_smoke": str(fstart.relative_to(KK_ROOT)).replace("\\", "/"),
        "persona_columns": len(personas),
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
