"""yPAD Run=Y shrink/restore — parity with BRAHL.py Heal tab."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = "y/qoa_web/qoa_web.json"


def _resolve_y1_paths(suite_config: str = DEFAULT_SUITE) -> list[Path]:
    cfg_path = KK_ROOT / suite_config.replace("/", "\\")
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Suite config not found: {suite_config}")
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for rel in data.get("input_files", {}).get("yPlans", []):
        p = KK_ROOT / rel.replace("/", "\\")
        if p.is_file():
            paths.append(p)
    if not paths:
        raise FileNotFoundError("No y1Plans files in suite config")
    return paths


def failed_plan_ids(run_name: str) -> set[str]:
    run_dir = KK_ROOT / "z" / run_name
    results = next(run_dir.glob("*_zResults.csv"), None) if run_dir.is_dir() else None
    if not results:
        return set()
    failed: set[str] = set()
    with results.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("Result") or "").strip().lower() == "fail":
                pid = (row.get("PlanId") or "").strip()
                if pid:
                    failed.add(pid)
    return failed


def plan_stats(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    """Count y1Plans rows for a suite."""
    total = run_y = run_n = reuse = 0
    ypaths: list[str] = []
    for plans_path in _resolve_y1_paths(suite_config):
        ypaths.append(plans_path.relative_to(KK_ROOT).as_posix())
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if not pid:
                    continue
                total += 1
                if pid.startswith("PReuse_"):
                    reuse += 1
                run = (row.get("Run") or "").strip().upper()
                if run == "Y":
                    run_y += 1
                elif run == "N":
                    run_n += 1
    return {
        "plan_total": total,
        "plan_run_y": run_y,
        "plan_run_n": run_n,
        "plan_reuse": reuse,
        "yplans_paths": ypaths,
    }


def all_plan_ids(suite_config: str = DEFAULT_SUITE) -> set[str]:
    ids: set[str] = set()
    for plans_path in _resolve_y1_paths(suite_config):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if pid and not pid.startswith("PReuse_"):
                    ids.add(pid)
    return ids


def _edit_run_flags(
    run_y_ids: set[str] | None,
    run_n_ids: set[str] | None,
    suite_config: str = DEFAULT_SUITE,
) -> int:
    changed = 0
    for plans_path in _resolve_y1_paths(suite_config):
        rows: list[dict[str, str]] = []
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            for row in reader:
                pid = (row.get("PlanId") or "").strip()
                if pid.startswith("PReuse_"):
                    if (row.get("Run") or "").upper() != "N":
                        row["Run"] = "N"
                        changed += 1
                elif run_y_ids is not None and pid in run_y_ids and (row.get("Run") or "").upper() != "Y":
                    row["Run"] = "Y"
                    changed += 1
                elif run_n_ids is not None and pid in run_n_ids and (row.get("Run") or "").upper() != "N":
                    row["Run"] = "N"
                    changed += 1
                rows.append(row)
        with plans_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    return changed


def shrink_to_failures(run_name: str, suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    failed = failed_plan_ids(run_name)
    if not failed:
        return {"ok": False, "error": "No failures in run", "run_y": 0, "run_n": 0, "changed": 0}
    all_ids = all_plan_ids(suite_config)
    pass_ids = all_ids - failed
    changed = _edit_run_flags(run_y_ids=failed, run_n_ids=pass_ids, suite_config=suite_config)
    return {
        "ok": True,
        "run_y": len(failed),
        "run_n": len(pass_ids),
        "changed": changed,
        "failed_plans": sorted(failed),
    }


def restore_all_run_y(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    run_y = all_plan_ids(suite_config)
    changed = _edit_run_flags(run_y_ids=run_y, run_n_ids=None, suite_config=suite_config)
    return {"ok": True, "run_y": len(run_y), "changed": changed}


def list_automation_plans(suite_config: str = DEFAULT_SUITE) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for plans_path in _resolve_y1_paths(suite_config):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if not pid or pid.startswith("PReuse_"):
                    continue
                run = (row.get("Run") or "").strip().upper()
                if run != "Y":
                    continue
                tags = (row.get("Tags") or "").strip()
                out.append(
                    {
                        "planId": pid,
                        "planName": (row.get("PlanName") or pid).strip(),
                        "tags": tags,
                        "output": (row.get("Output") or "").strip(),
                        "kind": "automation",
                    }
                )
    return out


_SHEET_KEYS = {
    "plans": "yPlans",
    "actions": "yActions",
    "designs": "yDesigns",
}


def _resolve_suite_config(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    cfg_path = KK_ROOT / suite_config.replace("/", "\\")
    if not cfg_path.is_file():
        raise FileNotFoundError(f"Suite config not found: {suite_config}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def _resolve_sheet_paths(suite_config: str, sheet: str) -> list[Path]:
    if sheet not in _SHEET_KEYS:
        raise ValueError(f"Unknown sheet: {sheet}")
    data = _resolve_suite_config(suite_config)
    key = _SHEET_KEYS[sheet]
    paths: list[Path] = []
    for rel in data.get("input_files", {}).get(key, []):
        p = KK_ROOT / rel.replace("/", "\\")
        if p.is_file():
            paths.append(p)
    if not paths:
        raise FileNotFoundError(f"No {key} files in suite config")
    return paths


def _read_csv_file(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fieldnames, rows


def read_ypad_sheet(suite_config: str, sheet: str) -> dict[str, Any]:
    """Read y1Plans, y2Actions, or y3Designs for a suite."""
    paths = _resolve_sheet_paths(suite_config, sheet)
    all_headers: list[str] = []
    all_rows: list[dict[str, str]] = []
    rel_paths: list[str] = []
    for p in paths:
        rel_paths.append(p.relative_to(KK_ROOT).as_posix())
        headers, rows = _read_csv_file(p)
        if not all_headers:
            all_headers = headers
        all_rows.extend(rows)
    return {
        "sheet": sheet,
        "headers": all_headers,
        "rows": all_rows,
        "paths": rel_paths,
        "row_count": len(all_rows),
    }


_ENV_TYPE_MARKERS = {"env", "secure", "credential", "secret", "token"}
_ENV_NAME_MARKERS = ("password", "secret", "token", "api_key", "credential", "client_secret")


def _is_env_design_row(row: dict[str, str]) -> bool:
    typ = (row.get("Type") or "").strip().lower()
    if typ in _ENV_TYPE_MARKERS:
        return True
    name = (row.get("DataName") or "").strip().lower()
    return any(m in name for m in _ENV_NAME_MARKERS)


def read_env_example(suite_config: str = DEFAULT_SUITE) -> dict[str, Any]:
    """ENV tab: credential/env rows from y3 + FoXYiZ .env.example."""
    designs = read_ypad_sheet(suite_config, "designs")
    env_rows = [r for r in designs["rows"] if _is_env_design_row(r)]
    example_path = KK_ROOT / "f" / ".env.example"
    example_text = ""
    if example_path.is_file():
        example_text = example_path.read_text(encoding="utf-8")
    lines: list[str] = []
    if example_text.strip():
        lines.append("# FoXYiZ / BRAHL — copy f/.env.example to f/.env")
        lines.append(example_text.strip())
    if env_rows:
        if lines:
            lines.append("")
        lines.append("# From y3Designs (credentials / environment)")
        for row in env_rows:
            name = (row.get("DataName") or "VAR").upper()
            val = (row.get("D1") or row.get("D2") or "").strip()
            if val and not val.startswith("http"):
                lines.append(f'{name}="{val}"')
            elif val:
                lines.append(f"# {name}={val}")
            else:
                lines.append(f'{name}=""')
    return {
        "sheet": "env",
        "headers": designs["headers"],
        "rows": env_rows,
        "env_example": "\n".join(lines) if lines else "# No ENV variables defined yet.\nOPENAI_API_KEY=",
        "paths": designs["paths"],
        "row_count": len(env_rows),
    }


def write_ypad_sheet(
    suite_config: str,
    sheet: str,
    rows: list[dict[str, str]],
    headers: list[str] | None = None,
) -> dict[str, Any]:
    """Write rows back to the first CSV path for a sheet (single-file suites)."""
    paths = _resolve_sheet_paths(suite_config, sheet)
    target = paths[0]
    if headers is None:
        headers, _ = _read_csv_file(target)
        if not headers and rows:
            headers = list(rows[0].keys())
    with target.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    rel = target.relative_to(KK_ROOT).as_posix()
    return {"ok": True, "path": rel, "row_count": len(rows)}
