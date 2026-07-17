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


def test_extract_patches_bare_json():
    md = '## Heal\n\n{"patches":[{"sheet":"actions","match":{"PlanId":"P1","StepId":"1"},"set":{"Input":"x"},"class":"T1"}]}'
    patches = heal_apply.extract_patches_from_markdown(md)
    assert len(patches) == 1
    assert patches[0]["set"]["Input"] == "x"


def test_run_flag_blocked():
    suite = "y/Math/Math.json"
    data = read_ypad_sheet(suite, "plans")
    row = next(r for r in data["rows"] if (r.get("Run") or "").upper() == "Y")
    patches = [
        {
            "sheet": "y1Plans",
            "match": {"PlanId": row.get("PlanId")},
            "set": {"Run": "N", "Tags": row.get("Tags") or "Smoke"},
            "class": "T1",
        }
    ]
    prev = heal_apply.apply_heal_patches(suite, patches, dry_run=True)
    for c in prev["changes"]:
        if c.get("status") in ("would_apply", "applied"):
            assert "Run" not in (c.get("after") or {})
            assert "Tags" in (c.get("after") or {})


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
