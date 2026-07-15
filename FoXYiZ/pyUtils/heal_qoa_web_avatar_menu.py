"""Heal qoa_web yPAD for slim top bar (avatar bar hidden → account menu role switch)."""
from __future__ import annotations

from pathlib import Path

Y = Path(__file__).resolve().parents[1] / "y" / "qoa_web"


def ui9(name: str, val: str) -> str:
    return "UI," + name + "," + ",".join([val] * 9) + "\n"


def patch_designs() -> None:
    path = Y / "y3Designs.csv"
    lines = path.read_text(encoding="utf-8").splitlines(True)
    retarget = {
        "avatar_client_bar_btn": "css=#user-menu-role-creator",
        "avatar_hitl_bar_btn": "css=#user-menu-role-hunter",
        "avatar_consultant_bar_btn": "css=#user-menu-role-hunter",
        "avatar_networker_bar_btn": "css=.user-menu-item[data-user-action='nalanda']",
        "avatar_client_label_locator": "css=#user-menu-role-creator",
        "avatar_hitl_label_locator": "css=#user-menu-role-hunter",
        "avatar_networker_label_locator": "css=.user-menu-item[data-user-action='nalanda']",
        "avatar_creator_label_expected": "View as Creator",
        "avatar_hunter_label_expected": "View as QA Hunter",
        "avatar_nalanda_label_expected": "Nalanda",
    }
    out: list[str] = []
    for line in lines:
        hit = False
        for key, val in retarget.items():
            if line.startswith(f"UI,{key},"):
                out.append(ui9(key, val))
                hit = True
                break
        if not hit:
            out.append(line)
    body = "".join(out)
    if "UI,user_menu_btn_locator," not in body:
        body += ui9("user_menu_btn_locator", "css=#user-menu-btn")
    path.write_text(body, encoding="utf-8")
    print("y3Designs retargeted to account menu")


def patch_actions() -> None:
    path = Y / "y2Actions.csv"
    a = path.read_text(encoding="utf-8")

    old_ready = (
        "PReuse_qoa_web_ClientReady,1,Persona ready,xReuse,PReuse_PersonaReady,,,,y\n"
        "PReuse_qoa_web_ClientReady,2,Click Client if needed,xUI,xClick,avatar_client_bar_btn,,,y\n"
        "PReuse_qoa_web_ClientReady,3,Verify topbar Projects label,xUI,xGetText,topbar_project_label_locator,,projects_label_expected,y"
    )
    new_ready = (
        "PReuse_qoa_web_ClientReady,1,Persona ready,xReuse,PReuse_PersonaReady,,,,y\n"
        "PReuse_qoa_web_ClientReady,2,Verify topbar Projects label,xUI,xGetText,topbar_project_label_locator,,projects_label_expected,y"
    )
    # also handle already-2-step with click still present as step2 label variant
    if old_ready in a:
        a = a.replace(old_ready, new_ready)
        print("ClientReady: removed hidden avatar click")
    elif "Click Client if needed,xUI,xClick,avatar_client_bar_btn" in a:
        a = a.replace(
            "PReuse_qoa_web_ClientReady,2,Click Client if needed,xUI,xClick,avatar_client_bar_btn,,,y\n",
            "",
        )
        # renumber step 3 -> 2 if needed
        a = a.replace(
            "PReuse_qoa_web_ClientReady,3,Verify topbar Projects label",
            "PReuse_qoa_web_ClientReady,2,Verify topbar Projects label",
        )
        print("ClientReady: stripped click line")
    else:
        print("ClientReady already slim or unknown shape")

    old_av = (
        "PWeb_Avatar_ThreeBar,1,Client ready,xReuse,PReuse_qoa_web_ClientReady,,,,y\n"
        "PWeb_Avatar_ThreeBar,2,Reload home,xUI,xNavigate,profile_url,,,y\n"
        "PWeb_Avatar_ThreeBar,3,Wait for shell,xTime,xTimeWait,3,,,y\n"
        "PWeb_Avatar_ThreeBar,4,Verify Creator label,xUI,xGetText,avatar_client_label_locator,,avatar_creator_label_expected,y\n"
        "PWeb_Avatar_ThreeBar,5,Verify QA Hunter label,xUI,xGetText,avatar_hitl_label_locator,,avatar_hunter_label_expected,y\n"
        "PWeb_Avatar_ThreeBar,6,Verify Nalanda label,xUI,xGetText,avatar_networker_label_locator,,avatar_nalanda_label_expected,y"
    )
    new_av = (
        "PWeb_Avatar_ThreeBar,1,Client ready,xReuse,PReuse_qoa_web_ClientReady,,,,y\n"
        "PWeb_Avatar_ThreeBar,2,Open account menu,xUI,xClick,user_menu_btn_locator,,,y\n"
        "PWeb_Avatar_ThreeBar,3,Verify View as Creator,xUI,xGetText,avatar_client_label_locator,,avatar_creator_label_expected,y\n"
        "PWeb_Avatar_ThreeBar,4,Verify View as QA Hunter,xUI,xGetText,avatar_hitl_label_locator,,avatar_hunter_label_expected,y\n"
        "PWeb_Avatar_ThreeBar,5,Verify Nalanda menu,xUI,xGetText,avatar_networker_label_locator,,avatar_nalanda_label_expected,y"
    )
    if old_av in a:
        a = a.replace(old_av, new_av)
        print("Avatar_ThreeBar -> account menu")
    else:
        print("WARN Avatar_ThreeBar block not found")

    a = a.replace(
        "PWeb_Nalanda_Panel,4,Click Nalanda avatar,xUI,xClick,avatar_networker_bar_btn,,,y",
        "PWeb_Nalanda_Panel,4,Open account menu,xUI,xClick,user_menu_btn_locator,,,y\n"
        "PWeb_Nalanda_Panel,5,Click Nalanda,xUI,xClick,avatar_networker_bar_btn,,,y",
    )

    path.write_text(a, encoding="utf-8")
    print("y2Actions healed")


if __name__ == "__main__":
    patch_designs()
    patch_actions()
