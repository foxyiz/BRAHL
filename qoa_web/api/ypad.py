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
