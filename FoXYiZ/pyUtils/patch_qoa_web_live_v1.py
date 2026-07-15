#!/usr/bin/env python3
"""BRAHL V1 — rebuild y/qoa_web_live verify gate for current /app UX.

Does NOT regenerate the 800 Journey library (V2). From KK/:
  python pyUtils/patch_qoa_web_live_v1.py
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from _paths import FOXYIZ_ROOT

ROOT = FOXYIZ_ROOT / "y" / "qoa_web_live"
DCOLS = [f"D{i}" for i in range(1, 10)]


def drow(data_name: str, value: str) -> dict[str, str]:
    return {"Type": "UI", "DataName": data_name, **{c: value for c in DCOLS}}


def main() -> None:
    designs_path = ROOT / "y3Designs.csv"
    with designs_path.open(encoding="utf-8-sig", newline="") as f:
        designs = list(csv.DictReader(f))
    by_name = {r["DataName"]: r for r in designs}

    def upsert(name: str, value: str) -> None:
        if name in by_name:
            for c in DCOLS:
                by_name[name][c] = value
        else:
            row = drow(name, value)
            designs.append(row)
            by_name[name] = row

    for r in designs:
        for c in DCOLS:
            if c in r and r[c]:
                r[c] = r[c].replace("suite=qoa_web", "suite=qoa_web_live")
                r[c] = r[c].replace("y/qoa_web/", "y/qoa_web_live/")
                # undo accidental live_live
                r[c] = r[c].replace("suite=qoa_web_live_live", "suite=qoa_web_live")
                r[c] = r[c].replace("y/qoa_web_live_live/", "y/qoa_web_live/")

    upsert("heal_heading_expected", "Heal — fix from Analyze")
    upsert("heal_edit_ypad_locator", "css=#btn-heal-edit-ypad")
    upsert("heal_edit_ypad_expected", "Edit yPAD on Build")
    upsert("heal_rerun_locator", "css=#btn-heal-rerun")
    upsert("heal_rerun_expected", "Rerun")
    upsert("heal_shrink_expected", "Shrink to failures")
    upsert("heal_failures_table_locator", "css=#heal-failures-body")
    upsert("loop_heading_expected", "Loop — BRAHL cycle")
    upsert("btn_loop_run_locator", "css=#btn-loop-run")
    upsert("btn_loop_run_expected", "Loop")
    upsert("loop_verify_checkbox_locator", "css=#loop-verify-full")
    upsert("loop_built_summary_locator", "css=#loop-built-summary")
    upsert("loop_times_fieldset_locator", "css=.loop-times-fieldset")
    upsert("build_strategy_locator", "css=#build-strategy")
    upsert("build_strategy_sub_locator", "css=#build-strategy .section-sub")
    upsert("build_strategy_expected", "Strategy / plan")
    upsert("ypad_cov_chips_locator", "css=#ypad-coverage-chips")
    upsert("ypad_cov_manual_locator", "css=.ypad-cov-chip[data-ypad-cov='manual']")
    upsert("ypad_cov_manual_expected", "Manual")
    upsert("analyze_fail_thead_locator", "css=.fail-table thead")
    upsert("analyze_fail_thead_expected", "Expected")
    upsert("rebuild_brahl_summary_locator", "css=#build-brahl-plan summary")
    upsert("rebuild_brahl_expected", "Rebuild BRAHL plan")
    upsert("budget_block_locator", "css=.budget-block")
    upsert("budget_block_expected", "QA wallet")
    upsert("api_runs_endpoint", "/api/runs?suite=qoa_web_live")

    with designs_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["Type", "DataName"] + DCOLS)
        w.writeheader()
        w.writerows(designs)
    print(f"designs {len(designs)}")

    plans_path = ROOT / "y1Plans.csv"
    with plans_path.open(encoding="utf-8-sig", newline="") as f:
        plans = list(csv.DictReader(f))
    existing = {p["PlanId"] for p in plans}

    new_plans = [
        ("PWeb_Build_Strategy", "Build Strategy / plan section visible", "D1", "Y", "Verify;qoa_web_live;Smoke;Build;V1", "strategy_ok"),
        ("PWeb_Build_CoverageChips", "Test coverage Manual chip visible", "D1", "Y", "Verify;qoa_web_live;Smoke;Build;yPAD;V1", "cov_chips_ok"),
        ("PWeb_Heal_EditYpadCta", "Heal Edit yPAD on Build CTA", "D1", "Y", "Verify;qoa_web_live;Smoke;Heal;V1", "heal_edit_ok"),
        ("PWeb_Heal_RerunCta", "Heal Rerun CTA", "D1", "Y", "Verify;qoa_web_live;Smoke;Heal;V1", "heal_rerun_ok"),
        ("PWeb_Loop_PrimaryButton", "Loop primary button and times", "D1", "Y", "Verify;qoa_web_live;Smoke;Loop;V1", "loop_btn_ok"),
        ("PWeb_Loop_BuiltSummary", "Loop Built summary from project", "D1", "Y", "Verify;qoa_web_live;Smoke;Loop;V1", "loop_built_ok"),
        ("PWeb_Analyze_FailColumns", "Analyze failure table has Expected column", "D1", "Y", "Verify;qoa_web_live;Smoke;Analyze;V1", "analyze_cols_ok"),
        ("PWeb_Rebuild_BrahlDetails", "Rebuild BRAHL plan details collapsed", "D1", "Y", "Verify;qoa_web_live;Build;V1", "rebuild_details_ok"),
    ]
    for row in new_plans:
        if row[0] not in existing:
            plans.append(
                {
                    "PlanId": row[0],
                    "PlanName": row[1],
                    "DesignId": row[2],
                    "Run": row[3],
                    "Tags": row[4],
                    "Output": row[5],
                }
            )
            existing.add(row[0])

    for p in plans:
        tags = [t.strip() for t in (p.get("Tags") or "").split(";") if t.strip()]
        # Prefer qoa_web_live on Verify gate rows
        if "Verify" in tags:
            tags = [("qoa_web_live" if t == "qoa_web" else t) for t in tags]
            if "qoa_web_live" not in tags:
                tags.append("qoa_web_live")
        # de-dupe preserve order
        seen: list[str] = []
        for t in tags:
            if t not in seen:
                seen.append(t)
        p["Tags"] = ";".join(seen)

    with plans_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output"])
        w.writeheader()
        w.writerows(plans)
    run_y = sum(1 for p in plans if p["Run"] == "Y")
    print(f"plans {len(plans)} Run=Y {run_y}")

    actions_path = ROOT / "y2Actions.csv"
    with actions_path.open(encoding="utf-8-sig", newline="") as f:
        actions = list(csv.DictReader(f))
    drop_ids = {r[0] for r in new_plans}
    actions = [a for a in actions if a["PlanId"] not in drop_ids]

    for a in actions:
        if a["PlanId"] == "PWeb_Panel_Heal" and a["StepInfo"] == "Verify shrink button":
            a["StepInfo"] = "Verify Heal heading"
            a["Input"] = "heal_heading_locator"
            a["Expected"] = "heal_heading_expected"
        if a["PlanId"] == "PWeb_Build_Budget" and "Verify budget" in a["StepInfo"]:
            a["Input"] = "budget_block_locator"
            a["Expected"] = "budget_block_expected"
        if a["PlanId"] == "PWeb_Panel_Loop" and a["StepInfo"] == "Verify Loop heading":
            a["Expected"] = "loop_heading_expected"

    cols = [
        "PlanId",
        "StepId",
        "StepInfo",
        "ActionType",
        "ActionName",
        "Input",
        "Output",
        "Expected",
        "Critical",
    ]
    new_actions = [
        ("PWeb_Build_Strategy", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Build_Strategy", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
        ("PWeb_Build_Strategy", 3, "Verify Strategy heading", "xUI", "xGetText", "build_strategy_sub_locator", "", "build_strategy_expected", "y"),
        ("PWeb_Build_CoverageChips", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Build_CoverageChips", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
        ("PWeb_Build_CoverageChips", 3, "Verify Manual chip", "xUI", "xGetText", "ypad_cov_manual_locator", "", "ypad_cov_manual_expected", "y"),
        ("PWeb_Heal_EditYpadCta", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Heal_EditYpadCta", 2, "Click Heal", "xUI", "xClick", "nav_heal_btn", "", "", "y"),
        ("PWeb_Heal_EditYpadCta", 3, "Wait", "xTime", "xTimeWait", "2", "", "", "y"),
        ("PWeb_Heal_EditYpadCta", 4, "Verify Edit yPAD CTA", "xUI", "xGetText", "heal_edit_ypad_locator", "", "heal_edit_ypad_expected", "y"),
        ("PWeb_Heal_RerunCta", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Heal_RerunCta", 2, "Click Heal", "xUI", "xClick", "nav_heal_btn", "", "", "y"),
        ("PWeb_Heal_RerunCta", 3, "Wait", "xTime", "xTimeWait", "2", "", "", "y"),
        ("PWeb_Heal_RerunCta", 4, "Verify Rerun CTA", "xUI", "xGetText", "heal_rerun_locator", "", "heal_rerun_expected", "y"),
        ("PWeb_Loop_PrimaryButton", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Loop_PrimaryButton", 2, "Click Loop", "xUI", "xClick", "nav_loop_btn", "", "", "y"),
        ("PWeb_Loop_PrimaryButton", 3, "Wait", "xTime", "xTimeWait", "2", "", "", "y"),
        ("PWeb_Loop_PrimaryButton", 4, "Verify Loop heading", "xUI", "xGetText", "loop_heading_locator", "", "loop_heading_expected", "y"),
        ("PWeb_Loop_PrimaryButton", 5, "Verify Loop button", "xUI", "xGetText", "btn_loop_run_locator", "", "btn_loop_run_expected", "y"),
        ("PWeb_Loop_BuiltSummary", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Loop_BuiltSummary", 2, "Click Loop", "xUI", "xClick", "nav_loop_btn", "", "", "y"),
        ("PWeb_Loop_BuiltSummary", 3, "Wait", "xTime", "xTimeWait", "2", "", "", "y"),
        ("PWeb_Loop_BuiltSummary", 4, "Verify Built block", "xUI", "xGetText", "loop_built_summary_locator", "", "Built", "y"),
        ("PWeb_Analyze_FailColumns", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Analyze_FailColumns", 2, "Click Analyze", "xUI", "xClick", "nav_analyze_btn", "", "", "y"),
        ("PWeb_Analyze_FailColumns", 3, "Wait", "xTime", "xTimeWait", "2", "", "", "y"),
        ("PWeb_Analyze_FailColumns", 4, "Verify Expected column", "xUI", "xGetText", "analyze_fail_thead_locator", "", "analyze_fail_thead_expected", "y"),
        ("PWeb_Rebuild_BrahlDetails", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
        ("PWeb_Rebuild_BrahlDetails", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
        ("PWeb_Rebuild_BrahlDetails", 3, "Verify Rebuild details", "xUI", "xGetText", "rebuild_brahl_summary_locator", "", "rebuild_brahl_expected", "y"),
    ]
    for t in new_actions:
        actions.append(dict(zip(cols, t)))

    with actions_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(actions)
    print(f"actions {len(actions)}")

    suite = {
        "input_files": {
            "yPlans": [
                "y/qoa_web_live/y1Plans.csv",
                "y/qoa_web_live/y1Plans_journey.csv",
            ],
            "yActions": [
                "y/qoa_web_live/y2Actions.csv",
                "y/qoa_web_live/y2Actions_journey.csv",
            ],
            "yDesigns": ["y/qoa_web_live/y3Designs.csv"],
        },
        "name": "qoa_web_live",
        "description": "BRAHL Arena live gate (V1 verify) + Journey library (V2 re-BRAHL). Current /app UX.",
        "version": "1.3.0-v1",
        "url": "http://127.0.0.1:8765/",
        "journey_plans": 800,
        "brahl_version": "v1",
    }
    (ROOT / "qoa_web_live.json").write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    gate = {
        "input_files": {
            "yPlans": ["y/qoa_web_live/y1Plans.csv"],
            "yActions": ["y/qoa_web_live/y2Actions.csv"],
            "yDesigns": ["y/qoa_web_live/y3Designs.csv"],
        },
        "name": "qoa_web_live",
        "description": "BRAHL live verify gate V1 only (no journey) — Analyze/Heal/Loop/Build current UX",
        "version": "1.3.0-v1",
        "url": "http://127.0.0.1:8765/",
    }
    (ROOT / "qoa_web_verify_gate.json").write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    old = ROOT / "qoa_web.json"
    if old.exists():
        old.unlink()
        print("removed stale qoa_web.json")

    print("V1 patch complete")


if __name__ == "__main__":
    main()
