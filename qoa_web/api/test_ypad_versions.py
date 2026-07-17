"""Tests for immutable yPAD version snapshots."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import ypad as ypad_store
import ypad_versions as versions


MATH = "y/Math/Math.json"


def test_snapshot_diff_restore_roundtrip(tmp_path: Path, monkeypatch) -> None:
    # Work on a disposable copy of Math under tmp so we do not mutate the real suite
    src = Path(ypad_store.resolve_repo("y/Math"))
    dest = tmp_path / "y" / "MathCopy"
    shutil.copytree(src, dest)
    cfg_rel = "y/MathCopy/Math.json"
    # Rewrite suite config paths inside copy
    cfg = dest / "Math.json"
    text = cfg.read_text(encoding="utf-8").replace("y/Math/", "y/MathCopy/")
    cfg.write_text(text, encoding="utf-8")
    monkeypatch.setattr(ypad_store, "resolve_repo", lambda rel: tmp_path / Path(str(rel).replace("\\", "/")))
    monkeypatch.setattr(versions, "resolve_repo", lambda rel: tmp_path / Path(str(rel).replace("\\", "/")))
    monkeypatch.setattr(
        versions,
        "_resolve_cfg_path",
        lambda suite_config: tmp_path / Path(str(suite_config).replace("\\", "/")),
    )
    monkeypatch.setattr(
        ypad_store,
        "_resolve_cfg_path",
        lambda suite_config: tmp_path / Path(str(suite_config).replace("\\", "/")),
    )

    # Fix resolve for sheet paths used by ypad_store
    from paths import resolve_repo as real_resolve

    def resolve_mixed(rel):
        s = str(rel).replace("\\", "/")
        if s.startswith("y/MathCopy"):
            return tmp_path / s
        return real_resolve(rel)

    monkeypatch.setattr(ypad_store, "resolve_repo", resolve_mixed)
    monkeypatch.setattr(versions, "resolve_repo", resolve_mixed)

    snap = versions.create_snapshot(cfg_rel, label="t1", author="tester")
    assert snap["immutable"] is True
    assert (dest / "versions" / snap["id"] / "manifest.json").is_file()

    plans = ypad_store.read_ypad_sheet(cfg_rel, "plans")
    assert plans["row_count"] > 0
    # Drop last plan to create a missing-row scenario after snapshot
    trimmed = plans["rows"][:-1]
    ypad_store.write_ypad_sheet(cfg_rel, "plans", trimmed, plans["headers"])

    diff = versions.diff_version(cfg_rel, snap["id"], sheet="plans")
    assert diff["counts"]["removed"] >= 1 or diff["counts"]["added"] == 0

    merged = versions.merge_missing(cfg_rel, snap["id"], sheet="plans")
    assert merged["merged"] >= 1

    # Snapshot again then restore earlier
    snap2 = versions.create_snapshot(cfg_rel, label="t2", author="tester")
    versions.restore_version(cfg_rel, snap["id"])
    after = ypad_store.read_ypad_sheet(cfg_rel, "plans")
    assert after["row_count"] == plans["row_count"]
    listed = versions.list_versions(cfg_rel)
    assert listed["count"] >= 2
    assert any(v["id"] == snap2["id"] for v in listed["versions"])


def test_annotate_plan_creator() -> None:
    row = versions.annotate_plan_creator({"PlanId": "P1"}, created_by="Planner")
    assert row["CreatedBy"] == "Planner"
    assert row["CreatedAt"]
