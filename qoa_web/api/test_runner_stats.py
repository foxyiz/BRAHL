"""Plan-level stats from zResults (not action rows)."""
from __future__ import annotations

import csv
from pathlib import Path

from runner import plan_stats_from_zresults


def _write_fixture(path: Path) -> None:
    rows = [
        {"PlanId": "P1", "StepId": "1", "Result": "Pass", "TimeTaken": "1.0"},
        {"PlanId": "P1", "StepId": "2", "Result": "Pass", "TimeTaken": "2.0"},
        {"PlanId": "P2", "StepId": "1", "Result": "Fail", "TimeTaken": "1.5"},
        {"PlanId": "P2", "StepId": "2", "Result": "Pass", "TimeTaken": "0.5"},
        {"PlanId": "P3", "StepId": "1", "Result": "Pass", "TimeTaken": "3.0"},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["PlanId", "StepId", "Result", "TimeTaken"])
        w.writeheader()
        w.writerows(rows)


def test_plan_stats_not_row_counts(tmp_path: Path) -> None:
    csv_path = tmp_path / "suite_zResults.csv"
    _write_fixture(csv_path)
    stats = plan_stats_from_zresults(csv_path)
    assert stats["total_plans"] == 3
    assert stats["passes"] == 2
    assert stats["fails"] == 1
    assert stats["fails"] <= stats["total_plans"]
    assert len(stats["failures"]) == 1
    assert stats["duration_sec"] == 8.0
