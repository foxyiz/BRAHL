"""Smoke tests for heal_apply (no OpenAI)."""

from __future__ import annotations

import heal_apply
from paths import resolve_repo
from ypad import read_ypad_sheet


def test_extract_patches():
    md = """## Heal\n\n```json\n{"patches":[{"sheet":"y2Actions","match":{"PlanId":"P1","StepId":"1"},"set":{"Expected":"ok"},"class":"T1"}]}\n```\n"""
    patches = heal_apply.extract_patches_from_markdown(md)
    assert len(patches) == 1
    assert patches[0]["set"]["Expected"] == "ok"


def test_dry_run_apply_math():
    suite = "y/Math/Math.json"
    assert resolve_repo(suite).is_file()
    data = read_ypad_sheet(suite, "actions")
    assert data["rows"]
    row = data["rows"][0]
    patches = [
        {
            "sheet": "y2Actions",
            "match": {"PlanId": row.get("PlanId"), "StepId": row.get("StepId")},
            "set": {"StepInfo": row.get("StepInfo") or ""},
            "class": "T1",
            "note": "noop",
        }
    ]
    prev = heal_apply.apply_heal_patches(suite, patches, dry_run=True)
    assert prev["applied"] >= 1
    assert prev["ok"] is True


def test_skip_a1():
    suite = "y/Math/Math.json"
    data = read_ypad_sheet(suite, "actions")
    row = data["rows"][0]
    patches = [
        {
            "sheet": "actions",
            "match": {"PlanId": row.get("PlanId"), "StepId": row.get("StepId")},
            "set": {"Expected": "x"},
            "class": "A1",
        }
    ]
    prev = heal_apply.apply_heal_patches(suite, patches, dry_run=True)
    assert prev["applied"] == 0
    assert prev["skipped"] >= 1
