"""Contract tests for source-safe yPAD writes and ENV redaction."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

import ypad as ypad_store


LIVE = "y/qoa_web_live/qoa_web_live.json"
MATH = "y/Math/Math.json"


def test_read_live_plans_annotates_sources() -> None:
    data = ypad_store.read_ypad_sheet(LIVE, "plans")
    assert data["multi_file"] is True
    assert len(data["paths"]) >= 2
    kinds = {s["kind"] for s in data["sources"]}
    assert "gate" in kinds
    assert "journey" in kinds
    assert all(r.get("_source") for r in data["rows"])
    assert all(r.get("_source_kind") in ("gate", "journey") for r in data["rows"])


def test_read_live_plans_source_kind_filter() -> None:
    gate = ypad_store.read_ypad_sheet(LIVE, "plans", source_kind="gate")
    journey = ypad_store.read_ypad_sheet(LIVE, "plans", source_kind="journey")
    assert gate["paths"] and all("_journey" not in p for p in gate["paths"])
    assert journey["paths"] and all("_journey" in p for p in journey["paths"])
    assert gate["row_count"] < journey["row_count"]


def test_write_multi_file_requires_source() -> None:
    data = ypad_store.read_ypad_sheet(LIVE, "plans", source_kind="gate")
    with pytest.raises(ValueError, match="explicit source"):
        ypad_store.write_ypad_sheet(LIVE, "plans", data["rows"], data["headers"])


def test_write_single_file_math_ok_without_source() -> None:
    data = ypad_store.read_ypad_sheet(MATH, "plans")
    assert data["multi_file"] is False
    # Round-trip same rows (no mutation)
    res = ypad_store.write_ypad_sheet(MATH, "plans", data["rows"], data["headers"])
    assert res["ok"] is True
    assert res["row_count"] == data["row_count"]


def test_write_gate_does_not_touch_journey(tmp_path: Path, monkeypatch) -> None:
    """Writing gate source must leave journey CSV byte-identical."""
    root = Path(ypad_store.resolve_repo("y/qoa_web_live"))
    journey = root / "y1Plans_journey.csv"
    before = journey.read_bytes()
    gate_data = ypad_store.read_ypad_sheet(LIVE, "plans", source_kind="gate")
    source = gate_data["paths"][0]
    # write identical rows back to gate only
    ypad_store.write_ypad_sheet(
        LIVE,
        "plans",
        gate_data["rows"],
        gate_data["headers"],
        source=source,
    )
    after = journey.read_bytes()
    assert before == after


def test_env_example_redacts_secret_values(tmp_path: Path, monkeypatch) -> None:
    suite_dir = tmp_path / "y" / "SecretSuite"
    suite_dir.mkdir(parents=True)
    designs = suite_dir / "y3Designs.csv"
    with designs.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Type", "DataName", "D1", "D2"])
        w.writeheader()
        w.writerow(
            {
                "Type": "secure",
                "DataName": "login_password",
                "D1": "super-secret-pass",
                "D2": "other-secret",
            }
        )
        w.writerow(
            {
                "Type": "UI",
                "DataName": "base_url",
                "D1": "http://127.0.0.1:8765/",
                "D2": "http://127.0.0.1:8765/",
            }
        )
    cfg = suite_dir / "SecretSuite.json"
    cfg.write_text(
        json.dumps(
            {
                "name": "SecretSuite",
                "input_files": {
                    "yPlans": [],
                    "yActions": [],
                    "yDesigns": ["y/SecretSuite/y3Designs.csv"],
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(ypad_store, "resolve_repo", lambda rel: tmp_path / Path(rel))
    # F_DIR .env.example may or may not exist — redaction still required
    env = ypad_store.read_env_example("y/SecretSuite/SecretSuite.json")
    assert env["redacted"] is True
    assert "super-secret-pass" not in env["env_example"]
    assert "other-secret" not in env["env_example"]
    secret_row = next(r for r in env["rows"] if r["DataName"] == "login_password")
    assert secret_row["D1"] == ""
    assert secret_row.get("_redacted") == "1"


def test_plan_tags_exact_match() -> None:
    assert ypad_store.plan_tags_exact_match("Smoke;Verify;qoa_web_live", "Smoke")
    assert not ypad_store.plan_tags_exact_match("Smoke;Verify", "oke")
    assert ypad_store.plan_tags_exact_match("Journey;Nav", "nav")
