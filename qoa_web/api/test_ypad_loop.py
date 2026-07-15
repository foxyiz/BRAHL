"""Loop shrink / restore baseline for lean Math suite."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import ypad as ypad_store

SUITE = "y/Math/Math.json"
LEAN_Y = {"Math_Addition", "Math_Multiplication", "Math_Modulo", "Math_Round"}


def _write_zresults(run_dir: Path, fails: set[str], passes: set[str]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "Math_zResults.csv"
    rows = []
    # Engine-style PlanIds with P prefix
    for pid in sorted(passes):
        rows.append({"PlanId": f"P{pid}", "StepId": "1", "Result": "Pass", "TimeTaken": "0.1"})
    for pid in sorted(fails):
        rows.append({"PlanId": f"P{pid}", "StepId": "1", "Result": "Fail", "TimeTaken": "0.2"})
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["PlanId", "StepId", "Result", "TimeTaken"])
        w.writeheader()
        w.writerows(rows)


def _run_flags(suite: str = SUITE) -> dict[str, str]:
    out: dict[str, str] = {}
    for plans_path in ypad_store._resolve_y1_paths(suite):
        with plans_path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = (row.get("PlanId") or "").strip()
                if pid:
                    out[pid] = (row.get("Run") or "").strip().upper()
    return out


def test_shrink_restore_math_roundtrip(tmp_path: Path, monkeypatch) -> None:
    # Isolate KK_ROOT-ish artifacts: monkeypatch baseline next to Math.json via suite path
    baseline = Path(ypad_store.resolve_repo("y/Math/Math_run_y_baseline.json"))
    if baseline.is_file():
        baseline.unlink()

    # Ensure lean Run=Y set
    ypad_store._edit_run_flags(run_y_ids=LEAN_Y, run_n_ids=set(), suite_config=SUITE)
    assert ypad_store.current_run_y_ids(SUITE) == LEAN_Y

    run_name = "20260714_phaseb_math_loop"
    z_dir = Path(ypad_store.resolve_repo(f"z/{run_name}"))
    fails = {"Math_Round"}
    passes = LEAN_Y - fails
    _write_zresults(z_dir, fails, passes)

    try:
        shrunk = ypad_store.shrink_to_failures(run_name, SUITE)
        assert shrunk["ok"] is True
        assert set(shrunk["failed_plans"]) == fails
        assert set(shrunk["baseline_run_y"]) == LEAN_Y
        flags = _run_flags()
        assert flags["Math_Round"] == "Y"
        assert flags["Math_Addition"] == "N"
        assert flags["Math_Multiplication"] == "N"
        assert flags["Math_Modulo"] == "N"

        restored = ypad_store.restore_all_run_y(SUITE)
        assert restored["ok"] is True
        assert restored["from_baseline"] is True
        assert restored["run_y"] == len(LEAN_Y)
        assert ypad_store.current_run_y_ids(SUITE) == LEAN_Y
    finally:
        # leave suite in clean lean Y state
        ypad_store._edit_run_flags(run_y_ids=LEAN_Y, run_n_ids=set(), suite_config=SUITE)
        if baseline.is_file():
            # keep baseline aligned with lean suite for UI Verify
            baseline.write_text(json.dumps({"run_y": sorted(LEAN_Y)}, indent=2) + "\n", encoding="utf-8")


def test_missing_suite_message() -> None:
    try:
        ypad_store._resolve_y1_paths("y/_missing_lean_suite/nope.json")
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as exc:
        msg = str(exc).lower()
        assert "not found" in msg
        assert "math" in msg or "lean" in msg
