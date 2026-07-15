"""Fix y3Designs corrupted by startswith('D') matching DataName."""
from __future__ import annotations

import csv
from pathlib import Path

Y3 = Path(__file__).resolve().parents[1] / "y" / "qoa_web_live" / "y3Designs.csv"


def dcols(row: dict) -> list[str]:
    return [c for c in row if c.startswith("D") and c[1:].isdigit()]


def main() -> None:
    rows = list(csv.DictReader(Y3.open(encoding="utf-8-sig")))
    # Repair rows where DataName was overwritten
    repaired = 0
    for r in rows:
        dn = r.get("DataName") or ""
        if dn == "css=.admin-brand h1":
            r["DataName"] = "admin_ecosystem_heading_locator"
            for c in dcols(r):
                r[c] = "css=.admin-brand h1"
            repaired += 1
        elif dn == "Admin Panel":
            r["DataName"] = "admin_ecosystem_heading_expected"
            for c in dcols(r):
                r[c] = "Admin Panel"
            repaired += 1
        elif dn.startswith("Build") and "qoa_web" in dn and "hitl" not in (r.get("DataName") or "").lower():
            # may already be wrong DataName
            pass

    # Ensure build_title_client_expected exists with ASCII hyphen to avoid em-dash mismatch
    by_name = {r["DataName"]: r for r in rows}
    title = "Build - qoa_web_live"
    # Check actual UI chars from a prior fail - they used unicode em dash. Try both via empty expected? Prefer exact from app.
    # App likely uses "Build — qoa_web_live" (em). We'll set empty Expected on Panel_Build instead for presence… but other plans need exact.
    # Use the same em dash character as UI.
    title_em = "Build \u2014 qoa_web_live"

    if "build_title_client_expected" not in by_name:
        # recreate from a template column set
        template = rows[0]
        new = {k: "" for k in template}
        new["Type"] = "UI"
        new["DataName"] = "build_title_client_expected"
        for c in dcols(template):
            new[c] = title_em
        rows.append(new)
        print("recreated build_title_client_expected")
    else:
        for c in dcols(by_name["build_title_client_expected"]):
            by_name["build_title_client_expected"][c] = title_em
        print("patched build_title_client_expected")

    if "admin_ecosystem_heading_locator" not in {r["DataName"] for r in rows}:
        template = rows[0]
        new = {k: "" for k in template}
        new["Type"] = "UI"
        new["DataName"] = "admin_ecosystem_heading_locator"
        for c in dcols(template):
            new[c] = "css=.admin-brand h1"
        rows.append(new)
    else:
        r = next(x for x in rows if x["DataName"] == "admin_ecosystem_heading_locator")
        for c in dcols(r):
            r[c] = "css=.admin-brand h1"

    if "admin_ecosystem_heading_expected" not in {r["DataName"] for r in rows}:
        template = rows[0]
        new = {k: "" for k in template}
        new["Type"] = "UI"
        new["DataName"] = "admin_ecosystem_heading_expected"
        for c in dcols(template):
            new[c] = "Admin Panel"
        rows.append(new)
    else:
        r = next(x for x in rows if x["DataName"] == "admin_ecosystem_heading_expected")
        for c in dcols(r):
            r[c] = "Admin Panel"

    with Y3.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    # verify
    names = {r["DataName"] for r in rows}
    print("repaired", repaired)
    print("has locator", "admin_ecosystem_heading_locator" in names)
    print("has expected", "admin_ecosystem_heading_expected" in names)
    print("has build title", "build_title_client_expected" in names)
    bt = next(r for r in rows if r["DataName"] == "build_title_client_expected")
    print("title D1 repr", repr(bt["D1"]))


if __name__ == "__main__":
    main()
