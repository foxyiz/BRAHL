"""Heal qoa_web_live smoke failures after Admin SPA move."""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "y" / "qoa_web_live"


def main() -> None:
    y3 = ROOT / "y3Designs.csv"
    rows = list(csv.DictReader(y3.open(encoding="utf-8-sig")))
    for r in rows:
        name = r.get("DataName")
        # Only D1..D9 — never touch DataName (startswith("D") would match it)
        dcols = [c for c in r if c.startswith("D") and c[1:].isdigit()]
        if name == "build_title_client_expected":
            for c in dcols:
                if r[c]:
                    r[c] = "Build \u2014 qoa_web_live"
        elif name == "admin_ecosystem_heading_locator":
            for c in dcols:
                if r[c]:
                    r[c] = "css=.admin-brand h1"
        elif name == "admin_ecosystem_heading_expected":
            for c in dcols:
                if r[c]:
                    r[c] = "Admin Panel"
    with y3.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print("y3Designs patched")

    y2 = ROOT / "y2Actions.csv"
    actions = list(csv.DictReader(y2.open(encoding="utf-8-sig")))
    fields = list(actions[0].keys())
    actions = [
        a
        for a in actions
        if not (a["PlanId"] == "PWeb_Admin_Ecosystem" and a.get("StepInfo") == "Return to Arena")
    ]
    out: list[dict] = []
    inserted = False
    for a in actions:
        out.append(a)
        if a["PlanId"] == "PWeb_Admin_Ecosystem" and str(a.get("StepId")) == "3":
            out.append(
                {
                    "PlanId": "PWeb_Admin_Ecosystem",
                    "StepId": "4",
                    "StepInfo": "Return to Arena",
                    "ActionType": "xUI",
                    "ActionName": "xNavigate",
                    "Input": "base_url",
                    "Output": "",
                    "Expected": "",
                    "Critical": "y",
                }
            )
            inserted = True
    with y2.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    print("admin return step", inserted)

    # Make ClientReady navigate every time by changing Input cache key via unique Output token —
    # actually engine caches resolved Input after design expand. Safer: insert Navigate as step 2
    # with Input base_url — first smoke still caches. Admin return is enough for cascade.
    # Also harden ClientReady: Navigate base_url before verify (helps when cache misses).
    actions2 = list(csv.DictReader(y2.open(encoding="utf-8-sig")))
    fields = list(actions2[0].keys())
    has_nav = any(
        a["PlanId"] == "PReuse_qoa_web_ClientReady" and a.get("StepInfo") == "Ensure Arena"
        for a in actions2
    )
    if not has_nav:
        rebuilt = []
        for a in actions2:
            if a["PlanId"] == "PReuse_qoa_web_ClientReady" and str(a.get("StepId")) == "1":
                rebuilt.append(a)
                rebuilt.append(
                    {
                        "PlanId": "PReuse_qoa_web_ClientReady",
                        "StepId": "2",
                        "StepInfo": "Ensure Arena",
                        "ActionType": "xUI",
                        "ActionName": "xNavigate",
                        "Input": "base_url",
                        "Output": "",
                        "Expected": "",
                        "Critical": "y",
                    }
                )
            elif a["PlanId"] == "PReuse_qoa_web_ClientReady" and str(a.get("StepId")) == "2":
                a = dict(a)
                a["StepId"] = "3"
                rebuilt.append(a)
            else:
                rebuilt.append(a)
        with y2.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            w.writeheader()
            w.writerows(rebuilt)
        print("ClientReady Ensure Arena step added")
    else:
        print("ClientReady already has Ensure Arena")

    y1 = ROOT / "y1Plans.csv"
    plans = list(csv.DictReader(y1.open(encoding="utf-8-sig")))
    for p in plans:
        if p["PlanId"] == "PWeb_Admin_Ecosystem":
            p["PlanName"] = "P6 Admin Panel loads (scoped admin SPA)"
    with y1.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(plans[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(plans)
    print("y1 renamed admin plan")


if __name__ == "__main__":
    main()
