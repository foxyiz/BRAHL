"""Patch qoa_web yPAD for Projects label, Run chips, GitHub — lean shared reuse update."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
Y = ROOT / "y" / "qoa_web"


def ui9(name: str, val: str) -> str:
    return "UI," + name + "," + ",".join([val] * 9)


def patch_designs() -> None:
    path = Y / "y3Designs.csv"
    lines = path.read_text(encoding="utf-8").splitlines(True)
    out: list[str] = []
    for line in lines:
        if line.startswith("UI,config_label_locator,"):
            out.append(ui9("config_label_locator", "css=.fstart-toolbar-label") + "\n")
        else:
            out.append(line)
    body = "".join(out)
    additions = [
        ui9("fstart_toolbar_locator", "css=.fstart-toolbar"),
        ui9("fstart_chip_row_locator", "css=#fstart-chip-row"),
        ui9("fstart_chip_locator", "css=.fstart-chip"),
        ui9("btn_run_parallel_locator", "css=#btn-run-parallel"),
        ui9("btn_fstart_edit_locator", "css=#btn-fstart-edit"),
        ui9("btn_fstart_new_locator", "css=#btn-fstart-new"),
        ui9("topbar_github_locator", "css=#topbar-github"),
        ui9("arena_cost_widget_locator", "css=#arena-cost-widget"),
        ui9("fstart_label_expected", "fStarts"),
        ui9("btn_run_expected", "Run"),
        ui9("btn_run_parallel_expected", "Run parallel"),
        ui9("topbar_github_expected", "GitHub"),
        ui9("projects_label_expected", "Projects"),
    ]
    for row in additions:
        key = row.split(",")[1]
        if f"UI,{key}," not in body:
            if not body.endswith("\n"):
                body += "\n"
            body += row + "\n"
    path.write_text(body, encoding="utf-8")
    print("y3Designs.csv OK")


def patch_actions() -> None:
    path = Y / "y2Actions.csv"
    a = path.read_text(encoding="utf-8")
    a2 = a.replace(
        "PReuse_qoa_web_ClientReady,3,Verify topbar challenge label,xUI,xGetText,topbar_project_label_locator,,My challenge,y",
        "PReuse_qoa_web_ClientReady,3,Verify topbar Projects label,xUI,xGetText,topbar_project_label_locator,,projects_label_expected,y",
    )
    if a2 == a:
        # already patched or variant text
        a2 = a.replace(",,My challenge,y", ",,projects_label_expected,y")
        print("ClientReady: fallback replace" if a2 != a else "WARN ClientReady")
    else:
        print("ClientReady -> Projects")

    if "PWeb_Panel_Run,4," not in a2:
        needle = "PWeb_Panel_Run,3,Verify Run heading,xUI,xGetText,run_heading_locator,,run_heading_expected,y\n"
        insert = needle + (
            "PWeb_Panel_Run,4,Verify fStarts label,xUI,xGetText,config_label_locator,,fstart_label_expected,y\n"
            "PWeb_Panel_Run,5,Verify fStart chips,xUI,xGetText,fstart_chip_row_locator,,,y\n"
            "PWeb_Panel_Run,6,Verify Run button,xUI,xGetText,btn_run_locator,,btn_run_expected,y\n"
            "PWeb_Panel_Run,7,Verify Run parallel,xUI,xGetText,btn_run_parallel_locator,,btn_run_parallel_expected,y\n"
            "PWeb_Panel_Run,8,Verify Edit fStart,xUI,xGetText,btn_fstart_edit_locator,,Edit,y\n"
        )
        if needle in a2:
            a2 = a2.replace(needle, insert)
            print("PWeb_Panel_Run expanded")
        else:
            print("WARN Panel_Run needle missing")

    if "PWeb_Shell_Github," not in a2:
        a2 += (
            "PWeb_Shell_Github,1,Client ready,xReuse,PReuse_qoa_web_ClientReady,,,,y\n"
            "PWeb_Shell_Github,2,Verify GitHub link,xUI,xGetText,topbar_github_locator,,topbar_github_expected,y\n"
        )
        print("PWeb_Shell_Github actions added")

    path.write_text(a2, encoding="utf-8")
    print("y2Actions.csv OK")


def patch_plans() -> None:
    path = Y / "y1Plans.csv"
    p = path.read_text(encoding="utf-8")
    if "PWeb_Shell_Github," in p:
        print("plan PWeb_Shell_Github exists")
        return
    line = "PWeb_Shell_Github,Top bar GitHub download link,D1,Y,Verify;qoa_web;Smoke;Shell,github_ok\n"
    if "PWeb_Footer_Health," in p:
        p = re.sub(r"(PWeb_Footer_Health,[^\n]+\n)", r"\1" + line, p, count=1)
    else:
        p += line
    path.write_text(p, encoding="utf-8")
    print("y1Plans.csv + PWeb_Shell_Github")


def main() -> None:
    patch_designs()
    patch_actions()
    patch_plans()


if __name__ == "__main__":
    main()
