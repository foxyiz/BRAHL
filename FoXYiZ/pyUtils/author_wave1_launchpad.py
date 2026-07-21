"""Author Wave 1 Base44 Launchpad yPAD suites (ops_overview depth)."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

FOXYIZ = Path(__file__).resolve().parents[1]
Y = FOXYIZ / "y"
FSTART = FOXYIZ / "f" / "fStart"
STAMP = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
BY = "QA_Hunter+BRAHL_Wave1"


def d9(val: str) -> list[str]:
    return [val] * 9


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_fstart(suite: str) -> None:
    cfg = {
        "configs": [f"y/{suite}/{suite}.json"],
        "thread_count": 1,
        "timeout": 20,
        "headless": True,
        "debug": False,
        "tags": ["Smoke", "UI", "Edge", "API", "Security", "Perf"],
        "capture": {"image": "on_fail", "video": "off", "video_fps": 2, "subdir": ""},
    }
    FSTART.mkdir(parents=True, exist_ok=True)
    (FSTART / f"{suite}.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def write_suite_json(suite: str, name: str, desc: str, url: str) -> None:
    cfg = {
        "input_files": {
            "yPlans": [f"y/{suite}/y1Plans.csv"],
            "yActions": [f"y/{suite}/y2Actions.csv"],
            "yDesigns": [f"y/{suite}/y3Designs.csv"],
        },
        "name": suite,
        "description": desc,
        "version": "1.0.0",
        "url": url,
    }
    out = Y / suite
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{suite}.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def y3_rows(rows: list[tuple[str, str, str]]) -> list[list]:
    out = []
    for typ, name, val in rows:
        out.append([typ, name, *d9(val)])
    return out


def plan(pid, name, tags, output, run="Y"):
    return [pid, name, "D1", run, tags, output, BY, STAMP]


def act(pid, step, info, atype, aname, inp="", out="", exp="", crit="Y"):
    return [pid, step, info, atype, aname, inp, out, exp, crit]


# ---------------------------------------------------------------------------
# LifeLeveled
# ---------------------------------------------------------------------------
def author_life_leveled() -> None:
    suite = "life_leveled"
    base = "https://life-leveled.base44.app"
    write_suite_json(suite, "LifeLeveled", "LifeLeveled life-skills platform — Smoke UI Edge API Security Perf", base + "/")
    write_fstart(suite)

    designs = y3_rows(
        [
            ("UI", "persona_id", "p1"),
            ("UI", "persona_code", "P1"),
            ("UI", "persona_name", "Life Learner"),
            ("UI", "persona_portfolio", "Home Learn Pricing Auth"),
            ("UI", "base_url", base + "/"),
            ("UI", "home_url", base + "/"),
            ("UI", "learn_url", base + "/learn"),
            ("UI", "pricing_url", base + "/pricing"),
            ("UI", "login_url", base + "/login"),
            ("UI", "register_url", base + "/register"),
            ("UI", "about_url", base + "/about"),
            ("UI", "privacy_url", base + "/privacy"),
            ("UI", "unknown_url", base + "/no-such-xyz-brahl"),
            ("UI", "api_host", base),
            ("UI", "ep_home", "/"),
            ("UI", "ep_favicon", "/favicon.ico"),
            ("UI", "ep_robots", "/robots.txt"),
            ("UI", "ep_unknown", "/no-such-xyz-brahl"),
            ("UI", "body_locator", "css=body"),
            ("UI", "btn_english", "xpath=//button[normalize-space()='English']"),
            ("UI", "page_title_home", "LifeLeveled"),
            ("UI", "page_title_learn", "Learning"),
            ("UI", "page_title_pricing", "Pricing"),
            ("UI", "page_title_login", "Login"),
            ("UI", "page_title_register", "Register"),
            ("UI", "text_tagline", "Level Up for Life"),
            ("UI", "text_choose_lang", "Choose your language"),
            ("UI", "text_become", "Become LifeLeveled"),
            ("UI", "text_build_plan", "Build My Readiness Plan"),
            ("UI", "text_explore", "Explore Skills"),
            ("UI", "text_nav_learn", "Learn"),
            ("UI", "text_nav_coach", "AI Coach"),
            ("UI", "text_pricing", "Pricing"),
            ("UI", "text_welcome", "Welcome back"),
            ("UI", "text_google", "Continue with Google"),
            ("UI", "text_create_account", "Create your account"),
            ("UI", "text_about", "Everyone Deserves Practical Guidance"),
            ("UI", "text_privacy", "Privacy Policy"),
            ("UI", "text_404", "Page Not Found"),
            ("UI", "text_learning", "Learning"),
            ("UI", "text_choose_support", "Choose the Support That Fits Your Journey"),
        ]
    )
    write_csv(Y / suite / "y3Designs.csv", ["Type", "DataName", *[f"D{i}" for i in range(1, 10)]], designs)

    reuse = "PReuse_Life_Open"
    plans = [
        plan(reuse, "Open Edge, pick English, load LifeLeveled", "Reuse", "site_loaded", "N"),
        plan("PLife_Smoke_Home", "Home after English: Become + CTAs", f"{suite};Smoke;Home;Landing", "home_ok"),
        plan("PLife_Smoke_Learn", "Learn hub semester programs", f"{suite};Smoke;Learn", "learn_ok"),
        plan("PLife_Smoke_Pricing", "Pricing journey support tiers", f"{suite};Smoke;Pricing", "pricing_ok"),
        plan("PLife_Smoke_Login", "Login welcome + Google", f"{suite};Smoke;Login;Auth", "login_ok"),
        plan("PLife_Smoke_Register", "Register create account", f"{suite};Smoke;Register;Auth", "register_ok"),
        plan("PLife_Smoke_About", "About mission page", f"{suite};Smoke;About", "about_ok"),
        plan("PLife_Smoke_Privacy", "Privacy policy page", f"{suite};Smoke;Privacy", "privacy_ok"),
        plan("PLife_Smoke_BrahlConclusion", "BRAHL conclusion — LifeLeveled shell ready", f"{suite};Smoke;BRAHL;Conclusion", "brahl_conclusion"),
        plan("PLife_UI_NavShell", "Nav Learn + AI Coach + Pricing", f"{suite};UI;Nav;Shell", "nav_ok"),
        plan("PLife_UI_HomeCTAs", "Home readiness CTAs present", f"{suite};UI;Home;CTA", "cta_ok"),
        plan("PLife_UI_LoginGoogle", "Login Continue with Google", f"{suite};UI;Auth;Google", "google_ok"),
        plan("PLife_Edge_Unknown404", "Unknown path shows Page Not Found", f"{suite};Edge;404", "edge_404"),
        plan("PLife_API_GetHome", "GET / returns 200", f"{suite};API;Home", "api_home"),
        plan("PLife_API_Favicon", "GET /favicon.ico returns 200", f"{suite};API;Favicon", "api_favicon"),
        plan("PLife_API_Robots", "GET /robots.txt returns 200", f"{suite};API;Robots", "api_robots"),
        plan("PLife_API_UnknownSpa", "GET unknown SPA route returns 200", f"{suite};API;404", "api_unknown"),
        plan("PLife_Sec_HttpsHost", "App served over https", f"{suite};Security;Landing", "sec_https"),
        plan("PLife_Perf_HomeLoad", "Home load under 20s after language", f"{suite};Perf;Home", "perf_home"),
        plan("PLife_Manual_AICoach", "HITL: AI Coach conversation", f"{suite};Manual;Coach;Hunt", "hitl_coach", "N"),
        plan("PLife_Manual_Onboarding", "HITL: Build My Readiness Plan flow", f"{suite};Manual;Onboarding;Hunt", "hitl_onboard", "N"),
    ]
    write_csv(
        Y / suite / "y1Plans.csv",
        ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"],
        plans,
    )

    actions = [
        act(reuse, 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act(reuse, 2, "Home", "xUI", "xNavigate", "base_url"),
        act(reuse, 3, "Wait lang", "xTime", "xTimeWait", "2"),
        act(reuse, 4, "English", "xUI", "xClick", "btn_english"),
        act(reuse, 5, "Wait home", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Home", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_Home", 2, "Title", "xUI", "xGetTitle", "", "", "page_title_home"),
        act("PLife_Smoke_Home", 3, "Become", "xUI", "xGetText", "body_locator", "", "text_become"),
        act("PLife_Smoke_Home", 4, "Build plan", "xUI", "xGetText", "body_locator", "", "text_build_plan"),
        act("PLife_Smoke_Home", 5, "Explore", "xUI", "xGetText", "body_locator", "", "text_explore"),
        act("PLife_Smoke_Learn", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_Learn", 2, "Learn", "xUI", "xNavigate", "learn_url"),
        act("PLife_Smoke_Learn", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Learn", 4, "Title", "xUI", "xGetTitle", "", "", "page_title_learn"),
        act("PLife_Smoke_Learn", 5, "Learning", "xUI", "xGetText", "body_locator", "", "text_learning"),
        act("PLife_Smoke_Pricing", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_Pricing", 2, "Pricing", "xUI", "xNavigate", "pricing_url"),
        act("PLife_Smoke_Pricing", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Pricing", 4, "Title", "xUI", "xGetTitle", "", "", "page_title_pricing"),
        act("PLife_Smoke_Pricing", 5, "Support", "xUI", "xGetText", "body_locator", "", "text_choose_support"),
        act("PLife_Smoke_Login", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PLife_Smoke_Login", 2, "Login", "xUI", "xNavigate", "login_url"),
        act("PLife_Smoke_Login", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Login", 4, "Welcome", "xUI", "xGetText", "body_locator", "", "text_welcome"),
        act("PLife_Smoke_Login", 5, "Google", "xUI", "xGetText", "body_locator", "", "text_google"),
        act("PLife_Smoke_Register", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PLife_Smoke_Register", 2, "Register", "xUI", "xNavigate", "register_url"),
        act("PLife_Smoke_Register", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Register", 4, "Create", "xUI", "xGetText", "body_locator", "", "text_create_account"),
        act("PLife_Smoke_Register", 5, "Google", "xUI", "xGetText", "body_locator", "", "text_google"),
        act("PLife_Smoke_About", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_About", 2, "About", "xUI", "xNavigate", "about_url"),
        act("PLife_Smoke_About", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_About", 4, "Mission", "xUI", "xGetText", "body_locator", "", "text_about"),
        act("PLife_Smoke_Privacy", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_Privacy", 2, "Privacy", "xUI", "xNavigate", "privacy_url"),
        act("PLife_Smoke_Privacy", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_Smoke_Privacy", 4, "Policy", "xUI", "xGetText", "body_locator", "", "text_privacy"),
        act("PLife_Smoke_BrahlConclusion", 1, "Open", "xReuse", reuse),
        act("PLife_Smoke_BrahlConclusion", 2, "Become", "xUI", "xGetText", "body_locator", "", "text_become"),
        act("PLife_Smoke_BrahlConclusion", 3, "API", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PLife_UI_NavShell", 1, "Open", "xReuse", reuse),
        act("PLife_UI_NavShell", 2, "Learn", "xUI", "xGetText", "body_locator", "", "text_nav_learn"),
        act("PLife_UI_NavShell", 3, "Coach", "xUI", "xGetText", "body_locator", "", "text_nav_coach"),
        act("PLife_UI_NavShell", 4, "Pricing", "xUI", "xGetText", "body_locator", "", "text_pricing"),
        act("PLife_UI_HomeCTAs", 1, "Open", "xReuse", reuse),
        act("PLife_UI_HomeCTAs", 2, "Build", "xUI", "xGetText", "body_locator", "", "text_build_plan"),
        act("PLife_UI_HomeCTAs", 3, "Explore", "xUI", "xGetText", "body_locator", "", "text_explore"),
        act("PLife_UI_LoginGoogle", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PLife_UI_LoginGoogle", 2, "Login", "xUI", "xNavigate", "login_url"),
        act("PLife_UI_LoginGoogle", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PLife_UI_LoginGoogle", 4, "Google", "xUI", "xGetText", "body_locator", "", "text_google"),
        act("PLife_Edge_Unknown404", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PLife_Edge_Unknown404", 2, "Unknown", "xUI", "xNavigate", "unknown_url"),
        act("PLife_Edge_Unknown404", 3, "Wait", "xTime", "xTimeWait", "2"),
        act("PLife_Edge_Unknown404", 4, "404", "xUI", "xGetText", "body_locator", "", "text_404"),
        act("PLife_API_GetHome", 1, "GET", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PLife_API_Favicon", 1, "GET", "xAPI", "xGet", "api_host;ep_favicon", "", "200"),
        act("PLife_API_Robots", 1, "GET", "xAPI", "xGet", "api_host;ep_robots", "", "200"),
        act("PLife_API_UnknownSpa", 1, "GET", "xAPI", "xGet", "api_host;ep_unknown", "", "200"),
        act("PLife_Sec_HttpsHost", 1, "Open", "xReuse", reuse),
        act("PLife_Sec_HttpsHost", 2, "Become", "xUI", "xGetText", "body_locator", "", "text_become"),
        act("PLife_Perf_HomeLoad", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PLife_Perf_HomeLoad", 2, "Start", "xUI", "xStartTimer"),
        act("PLife_Perf_HomeLoad", 3, "Nav", "xUI", "xNavigate", "base_url"),
        act("PLife_Perf_HomeLoad", 4, "Wait", "xTime", "xTimeWait", "2"),
        act("PLife_Perf_HomeLoad", 5, "English", "xUI", "xClick", "btn_english"),
        act("PLife_Perf_HomeLoad", 6, "Wait home", "xTime", "xTimeWait", "2"),
        act("PLife_Perf_HomeLoad", 7, "Stop", "xUI", "xStopTimer", "elapsed"),
        act("PLife_Perf_HomeLoad", 8, "Budget", "xUI", "xAssertLessThan", "{{step:7}};20000"),
        act("PLife_Perf_HomeLoad", 9, "Alive", "xUI", "xGetText", "body_locator", "", "text_become"),
        act("PLife_Manual_AICoach", 1, "Open", "xReuse", reuse, crit="N"),
        act("PLife_Manual_AICoach", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_nav_coach", "N"),
        act("PLife_Manual_Onboarding", 1, "Open", "xReuse", reuse, crit="N"),
        act("PLife_Manual_Onboarding", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_build_plan", "N"),
    ]
    write_csv(
        Y / suite / "y2Actions.csv",
        ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"],
        actions,
    )
    (Y / suite / "test plan.md").write_text(
        """# Test plan — LifeLeveled

| Area | Profile | Plans |
|------|---------|-------|
| Language gate → Home | Smoke | PLife_Smoke_Home |
| Learn / Pricing / About / Privacy | Smoke | PLife_Smoke_* |
| Auth | Smoke + UI | Login, Register, Google |
| Nav / CTAs | UI | NavShell, HomeCTAs |
| 404 | Edge | Unknown404 |
| Host probes | API + Security + Perf | GET + https + load |
| Coach / Onboarding | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/life_leveled.json
```
""",
        encoding="utf-8",
    )
    (Y / suite / "test strategy.md").write_text(
        "# Test strategy — life_leveled\n\nBase44 SPA with language gate. Fresh browser → click English → assert English shell.\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Space Planner
# ---------------------------------------------------------------------------
def author_space_planner() -> None:
    suite = "space_planner"
    base = "https://bulky-plan-draft-flow.base44.app"
    write_suite_json(suite, "Space Planner", "SpacePlanner CAD/3D planner — Smoke UI Edge API Security Perf", base + "/")
    write_fstart(suite)

    designs = y3_rows(
        [
            ("UI", "persona_id", "p1"),
            ("UI", "persona_code", "P1"),
            ("UI", "persona_name", "Home Designer"),
            ("UI", "persona_portfolio", "Landing Editor Docs"),
            ("UI", "base_url", base + "/"),
            ("UI", "editor_url", base + "/editor"),
            ("UI", "floor_url", base + "/floor-planner"),
            ("UI", "docs_url", base + "/docs"),
            ("UI", "room_url", base + "/room-planner"),
            ("UI", "garden_url", base + "/garden-planner"),
            ("UI", "unknown_url", base + "/no-such-xyz-brahl"),
            ("UI", "api_host", base),
            ("UI", "ep_home", "/"),
            ("UI", "ep_favicon", "/favicon.ico"),
            ("UI", "ep_robots", "/robots.txt"),
            ("UI", "ep_unknown", "/no-such-xyz-brahl"),
            ("UI", "body_locator", "css=body"),
            ("UI", "btn_start", "xpath=//button[contains(normalize-space(),'Start Drawing')]"),
            ("UI", "page_title_home", "Space Planner"),
            ("UI", "page_title_editor", "Editor"),
            ("UI", "page_title_docs", "Documentation"),
            ("UI", "page_title_floor", "Floor Planner"),
            ("UI", "text_brand", "SpacePlanner"),
            ("UI", "text_free", "Free Online Space Planner"),
            ("UI", "text_start", "Start Drawing"),
            ("UI", "text_example", "Open Example Plan"),
            ("UI", "text_no_signup", "No signup needed"),
            ("UI", "text_floor_nav", "Floor Planner"),
            ("UI", "text_docs", "How to use SpacePlanner"),
            ("UI", "text_editor_projects", "My projects"),
            ("UI", "text_editor_2d", "2D"),
            ("UI", "text_editor_3d", "3D"),
            ("UI", "text_symbol", "Symbol Library"),
            ("UI", "text_404", "Page Not Found"),
            ("UI", "text_floor_heading", "FLOOR PLANNER"),
        ]
    )
    write_csv(Y / suite / "y3Designs.csv", ["Type", "DataName", *[f"D{i}" for i in range(1, 10)]], designs)

    reuse = "PReuse_Space_Open"
    plans = [
        plan(reuse, "Open Edge and load SpacePlanner", "Reuse", "site_loaded", "N"),
        plan("PSpace_Smoke_Home", "Home free planner + Start Drawing", f"{suite};Smoke;Home;Landing", "home_ok"),
        plan("PSpace_Smoke_Editor", "Editor shell 2D/3D/symbols", f"{suite};Smoke;Editor", "editor_ok"),
        plan("PSpace_Smoke_Floor", "Floor Planner marketing page", f"{suite};Smoke;Floor", "floor_ok"),
        plan("PSpace_Smoke_Docs", "Docs how to use", f"{suite};Smoke;Docs", "docs_ok"),
        plan("PSpace_Smoke_BrahlConclusion", "BRAHL conclusion — SpacePlanner shell ready", f"{suite};Smoke;BRAHL;Conclusion", "brahl_conclusion"),
        plan("PSpace_UI_NavPlanners", "Nav Floor / Room / Garden", f"{suite};UI;Nav", "nav_ok"),
        plan("PSpace_UI_EditorModes", "Editor 2D and 3D modes", f"{suite};UI;Editor;Modes", "modes_ok"),
        plan("PSpace_UI_StartDrawing", "Start Drawing CTA on home", f"{suite};UI;Home;CTA", "cta_ok"),
        plan("PSpace_Edge_Unknown404", "Unknown path Page Not Found", f"{suite};Edge;404", "edge_404"),
        plan("PSpace_API_GetHome", "GET / returns 200", f"{suite};API;Home", "api_home"),
        plan("PSpace_API_Favicon", "GET favicon 200", f"{suite};API;Favicon", "api_favicon"),
        plan("PSpace_API_Robots", "GET robots 200", f"{suite};API;Robots", "api_robots"),
        plan("PSpace_API_UnknownSpa", "GET unknown SPA 200", f"{suite};API;404", "api_unknown"),
        plan("PSpace_Sec_HttpsHost", "HTTPS host", f"{suite};Security;Landing", "sec_https"),
        plan("PSpace_Perf_HomeLoad", "Home load under 15s", f"{suite};Perf;Home", "perf_home"),
        plan("PSpace_Manual_3DWalk", "HITL: 3D walkthrough in editor", f"{suite};Manual;Editor;3D", "hitl_3d", "N"),
        plan("PSpace_Manual_AIImport", "HITL: AI import photo to plan", f"{suite};Manual;AI;Import", "hitl_ai", "N"),
    ]
    write_csv(
        Y / suite / "y1Plans.csv",
        ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"],
        plans,
    )
    actions = [
        act(reuse, 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act(reuse, 2, "Home", "xUI", "xNavigate", "base_url"),
        act(reuse, 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PSpace_Smoke_Home", 1, "Open", "xReuse", reuse),
        act("PSpace_Smoke_Home", 2, "Title", "xUI", "xGetTitle", "", "", "page_title_home"),
        act("PSpace_Smoke_Home", 3, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PSpace_Smoke_Home", 4, "Free", "xUI", "xGetText", "body_locator", "", "text_free"),
        act("PSpace_Smoke_Home", 5, "Start", "xUI", "xGetText", "body_locator", "", "text_start"),
        act("PSpace_Smoke_Home", 6, "No signup", "xUI", "xGetText", "body_locator", "", "text_no_signup"),
        act("PSpace_Smoke_Editor", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PSpace_Smoke_Editor", 2, "Editor", "xUI", "xNavigate", "editor_url"),
        act("PSpace_Smoke_Editor", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PSpace_Smoke_Editor", 4, "Title", "xUI", "xGetTitle", "", "", "page_title_editor"),
        act("PSpace_Smoke_Editor", 5, "Projects", "xUI", "xGetText", "body_locator", "", "text_editor_projects"),
        act("PSpace_Smoke_Editor", 6, "2D", "xUI", "xGetText", "body_locator", "", "text_editor_2d"),
        act("PSpace_Smoke_Editor", 7, "Symbols", "xUI", "xGetText", "body_locator", "", "text_symbol"),
        act("PSpace_Smoke_Floor", 1, "Open", "xReuse", reuse),
        act("PSpace_Smoke_Floor", 2, "Floor", "xUI", "xNavigate", "floor_url"),
        act("PSpace_Smoke_Floor", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PSpace_Smoke_Floor", 4, "Heading", "xUI", "xGetText", "body_locator", "", "text_floor_heading"),
        act("PSpace_Smoke_Docs", 1, "Open", "xReuse", reuse),
        act("PSpace_Smoke_Docs", 2, "Docs", "xUI", "xNavigate", "docs_url"),
        act("PSpace_Smoke_Docs", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PSpace_Smoke_Docs", 4, "How", "xUI", "xGetText", "body_locator", "", "text_docs"),
        act("PSpace_Smoke_BrahlConclusion", 1, "Open", "xReuse", reuse),
        act("PSpace_Smoke_BrahlConclusion", 2, "Free", "xUI", "xGetText", "body_locator", "", "text_free"),
        act("PSpace_Smoke_BrahlConclusion", 3, "API", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PSpace_UI_NavPlanners", 1, "Open", "xReuse", reuse),
        act("PSpace_UI_NavPlanners", 2, "Floor", "xUI", "xGetText", "body_locator", "", "text_floor_nav"),
        act("PSpace_UI_NavPlanners", 3, "Room", "xUI", "xGetText", "body_locator", "", "Room Planner"),
        act("PSpace_UI_NavPlanners", 4, "Garden", "xUI", "xGetText", "body_locator", "", "Garden Planner"),
        act("PSpace_UI_EditorModes", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PSpace_UI_EditorModes", 2, "Editor", "xUI", "xNavigate", "editor_url"),
        act("PSpace_UI_EditorModes", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PSpace_UI_EditorModes", 4, "2D", "xUI", "xGetText", "body_locator", "", "text_editor_2d"),
        act("PSpace_UI_EditorModes", 5, "3D", "xUI", "xGetText", "body_locator", "", "text_editor_3d"),
        act("PSpace_UI_StartDrawing", 1, "Open", "xReuse", reuse),
        act("PSpace_UI_StartDrawing", 2, "CTA", "xUI", "xGetText", "body_locator", "", "text_start"),
        act("PSpace_UI_StartDrawing", 3, "Example", "xUI", "xGetText", "body_locator", "", "text_example"),
        act("PSpace_Edge_Unknown404", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PSpace_Edge_Unknown404", 2, "Unknown", "xUI", "xNavigate", "unknown_url"),
        act("PSpace_Edge_Unknown404", 3, "Wait", "xTime", "xTimeWait", "2"),
        act("PSpace_Edge_Unknown404", 4, "404", "xUI", "xGetText", "body_locator", "", "text_404"),
        act("PSpace_API_GetHome", 1, "GET", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PSpace_API_Favicon", 1, "GET", "xAPI", "xGet", "api_host;ep_favicon", "", "200"),
        act("PSpace_API_Robots", 1, "GET", "xAPI", "xGet", "api_host;ep_robots", "", "200"),
        act("PSpace_API_UnknownSpa", 1, "GET", "xAPI", "xGet", "api_host;ep_unknown", "", "200"),
        act("PSpace_Sec_HttpsHost", 1, "Open", "xReuse", reuse),
        act("PSpace_Sec_HttpsHost", 2, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PSpace_Perf_HomeLoad", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PSpace_Perf_HomeLoad", 2, "Start", "xUI", "xStartTimer"),
        act("PSpace_Perf_HomeLoad", 3, "Nav", "xUI", "xNavigate", "base_url"),
        act("PSpace_Perf_HomeLoad", 4, "Stop", "xUI", "xStopTimer", "elapsed"),
        act("PSpace_Perf_HomeLoad", 5, "Budget", "xUI", "xAssertLessThan", "{{step:4}};15000"),
        act("PSpace_Perf_HomeLoad", 6, "Alive", "xUI", "xGetText", "body_locator", "", "text_free"),
        act("PSpace_Manual_3DWalk", 1, "Open Edge", "xUI", "xOpenBrowser", "edge", crit="N"),
        act("PSpace_Manual_3DWalk", 2, "Editor", "xUI", "xNavigate", "editor_url", crit="N"),
        act("PSpace_Manual_3DWalk", 3, "Note", "xUI", "xGetText", "body_locator", "", "text_editor_3d", "N"),
        act("PSpace_Manual_AIImport", 1, "Open", "xReuse", reuse, crit="N"),
        act("PSpace_Manual_AIImport", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_start", "N"),
    ]
    write_csv(
        Y / suite / "y2Actions.csv",
        ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"],
        actions,
    )
    (Y / suite / "test plan.md").write_text(
        """# Test plan — Space Planner

| Area | Profile | Plans |
|------|---------|-------|
| Landing | Smoke | PSpace_Smoke_Home |
| Editor (`/editor`) | Smoke + UI | Editor, Modes |
| Floor / Docs | Smoke | Floor, Docs |
| 404 / API / Sec / Perf | Edge+API+Sec+Perf | probes |
| 3D / AI import | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/space_planner.json
```
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Haunted Castle
# ---------------------------------------------------------------------------
def author_haunted_castle() -> None:
    suite = "haunted_castle"
    base = "https://haunted-mansion.base44.app"
    write_suite_json(suite, "Haunted Castle", "Ziv's Haunted Castle 3D game — Smoke UI Edge API Security Perf", base + "/")
    write_fstart(suite)

    designs = y3_rows(
        [
            ("UI", "persona_id", "p1"),
            ("UI", "persona_code", "P1"),
            ("UI", "persona_name", "Castle Explorer"),
            ("UI", "persona_portfolio", "Landing Game Shell"),
            ("UI", "base_url", base + "/"),
            ("UI", "unknown_url", base + "/no-such-xyz-brahl"),
            ("UI", "api_host", base),
            ("UI", "ep_home", "/"),
            ("UI", "ep_favicon", "/favicon.ico"),
            ("UI", "ep_robots", "/robots.txt"),
            ("UI", "ep_unknown", "/no-such-xyz-brahl"),
            ("UI", "body_locator", "css=body"),
            ("UI", "btn_enter", "xpath=//button[contains(normalize-space(),'Enter the Castle')]"),
            ("UI", "btn_english", "xpath=//button[normalize-space()='English']"),
            ("UI", "page_title_home", "Ziv's Haunted Castle"),
            ("UI", "text_title", "Ziv's Haunted Castle"),
            ("UI", "text_enter", "Enter the Castle"),
            ("UI", "text_fog", "fog-covered castle"),
            ("UI", "text_wasd", "WASD"),
            ("UI", "text_hebrew", "עברית"),
            ("UI", "text_english", "English"),
            ("UI", "text_top", "BASE44 TOP APPS"),
            ("UI", "text_loading", "Untangling the mummy"),
            ("UI", "text_404", "Page Not Found"),
            ("UI", "text_played", "Played with AI"),
        ]
    )
    write_csv(Y / suite / "y3Designs.csv", ["Type", "DataName", *[f"D{i}" for i in range(1, 10)]], designs)

    reuse = "PReuse_Haunt_Open"
    plans = [
        plan(reuse, "Open Edge and load Haunted Castle", "Reuse", "site_loaded", "N"),
        plan("PHaunt_Smoke_Home", "Landing title + Enter CTA", f"{suite};Smoke;Home;Landing", "home_ok"),
        plan("PHaunt_Smoke_Controls", "WASD / arrow control copy", f"{suite};Smoke;Controls", "controls_ok"),
        plan("PHaunt_Smoke_LangToggle", "Hebrew + English language buttons", f"{suite};Smoke;Lang", "lang_ok"),
        plan("PHaunt_Smoke_TopBadge", "Base44 top apps badge", f"{suite};Smoke;Badge", "badge_ok"),
        plan("PHaunt_Smoke_BrahlConclusion", "BRAHL conclusion — Haunted Castle shell ready", f"{suite};Smoke;BRAHL;Conclusion", "brahl_conclusion"),
        plan("PHaunt_UI_EnterVisible", "Enter the Castle CTA visible", f"{suite};UI;CTA", "enter_ok"),
        plan("PHaunt_UI_EnterLoading", "Enter shows loading mummy progress", f"{suite};UI;Game;Load", "load_ok"),
        plan("PHaunt_Edge_Unknown404", "Unknown path Page Not Found", f"{suite};Edge;404", "edge_404"),
        plan("PHaunt_API_GetHome", "GET / 200", f"{suite};API;Home", "api_home"),
        plan("PHaunt_API_Favicon", "GET favicon 200", f"{suite};API;Favicon", "api_favicon"),
        plan("PHaunt_API_Robots", "GET robots 200", f"{suite};API;Robots", "api_robots"),
        plan("PHaunt_API_UnknownSpa", "GET unknown SPA 200", f"{suite};API;404", "api_unknown"),
        plan("PHaunt_Sec_HttpsHost", "HTTPS host", f"{suite};Security;Landing", "sec_https"),
        plan("PHaunt_Perf_HomeLoad", "Home load under 15s", f"{suite};Perf;Home", "perf_home"),
        plan("PHaunt_Manual_Explore3D", "HITL: explore castle WebGL", f"{suite};Manual;Game;3D", "hitl_3d", "N"),
        plan("PHaunt_Manual_Monsters", "HITL: approach monsters audio", f"{suite};Manual;Game;Audio", "hitl_audio", "N"),
    ]
    write_csv(
        Y / suite / "y1Plans.csv",
        ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"],
        plans,
    )
    actions = [
        act(reuse, 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act(reuse, 2, "Home", "xUI", "xNavigate", "base_url"),
        act(reuse, 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PHaunt_Smoke_Home", 1, "Open", "xReuse", reuse),
        act("PHaunt_Smoke_Home", 2, "Title", "xUI", "xGetTitle", "", "", "page_title_home"),
        act("PHaunt_Smoke_Home", 3, "Name", "xUI", "xGetText", "body_locator", "", "text_title"),
        act("PHaunt_Smoke_Home", 4, "Enter", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PHaunt_Smoke_Home", 5, "Fog", "xUI", "xGetText", "body_locator", "", "text_fog"),
        act("PHaunt_Smoke_Controls", 1, "Open", "xReuse", reuse),
        act("PHaunt_Smoke_Controls", 2, "WASD", "xUI", "xGetText", "body_locator", "", "text_wasd"),
        act("PHaunt_Smoke_LangToggle", 1, "Open", "xReuse", reuse),
        act("PHaunt_Smoke_LangToggle", 2, "HE", "xUI", "xGetText", "body_locator", "", "text_hebrew"),
        act("PHaunt_Smoke_LangToggle", 3, "EN", "xUI", "xGetText", "body_locator", "", "text_english"),
        act("PHaunt_Smoke_TopBadge", 1, "Open", "xReuse", reuse),
        act("PHaunt_Smoke_TopBadge", 2, "Badge", "xUI", "xGetText", "body_locator", "", "text_top"),
        act("PHaunt_Smoke_BrahlConclusion", 1, "Open", "xReuse", reuse),
        act("PHaunt_Smoke_BrahlConclusion", 2, "Enter", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PHaunt_Smoke_BrahlConclusion", 3, "API", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PHaunt_UI_EnterVisible", 1, "Open", "xReuse", reuse),
        act("PHaunt_UI_EnterVisible", 2, "CTA", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PHaunt_UI_EnterLoading", 1, "Open", "xReuse", reuse),
        act("PHaunt_UI_EnterLoading", 2, "Click enter", "xUI", "xClick", "btn_enter"),
        act("PHaunt_UI_EnterLoading", 3, "Wait load", "xTime", "xTimeWait", "3"),
        act("PHaunt_UI_EnterLoading", 4, "Loading", "xUI", "xGetText", "body_locator", "", "text_loading"),
        act("PHaunt_Edge_Unknown404", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PHaunt_Edge_Unknown404", 2, "Unknown", "xUI", "xNavigate", "unknown_url"),
        act("PHaunt_Edge_Unknown404", 3, "Wait", "xTime", "xTimeWait", "2"),
        act("PHaunt_Edge_Unknown404", 4, "404", "xUI", "xGetText", "body_locator", "", "text_404"),
        act("PHaunt_API_GetHome", 1, "GET", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PHaunt_API_Favicon", 1, "GET", "xAPI", "xGet", "api_host;ep_favicon", "", "200"),
        act("PHaunt_API_Robots", 1, "GET", "xAPI", "xGet", "api_host;ep_robots", "", "200"),
        act("PHaunt_API_UnknownSpa", 1, "GET", "xAPI", "xGet", "api_host;ep_unknown", "", "200"),
        act("PHaunt_Sec_HttpsHost", 1, "Open", "xReuse", reuse),
        act("PHaunt_Sec_HttpsHost", 2, "Title", "xUI", "xGetText", "body_locator", "", "text_title"),
        act("PHaunt_Perf_HomeLoad", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PHaunt_Perf_HomeLoad", 2, "Start", "xUI", "xStartTimer"),
        act("PHaunt_Perf_HomeLoad", 3, "Nav", "xUI", "xNavigate", "base_url"),
        act("PHaunt_Perf_HomeLoad", 4, "Stop", "xUI", "xStopTimer", "elapsed"),
        act("PHaunt_Perf_HomeLoad", 5, "Budget", "xUI", "xAssertLessThan", "{{step:4}};15000"),
        act("PHaunt_Perf_HomeLoad", 6, "Alive", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PHaunt_Manual_Explore3D", 1, "Open", "xReuse", reuse, crit="N"),
        act("PHaunt_Manual_Explore3D", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_enter", "N"),
        act("PHaunt_Manual_Monsters", 1, "Open", "xReuse", reuse, crit="N"),
        act("PHaunt_Manual_Monsters", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_fog", "N"),
    ]
    write_csv(
        Y / suite / "y2Actions.csv",
        ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"],
        actions,
    )
    (Y / suite / "test plan.md").write_text(
        """# Test plan — Ziv's Haunted Castle

| Area | Profile | Plans |
|------|---------|-------|
| Landing | Smoke | Home, Controls, Lang, Badge |
| Enter loading | UI | EnterLoading (mummy progress) |
| 404 / API / Sec / Perf | Edge+API+Sec+Perf | probes |
| WebGL explore | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/haunted_castle.json
```
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Creatop
# ---------------------------------------------------------------------------
def author_creatop() -> None:
    suite = "creatop"
    base = "https://creatop.base44.app"
    write_suite_json(suite, "Creatop", "Creatop Hebrew RTL studio portfolio — Smoke UI Edge API Security Perf", base + "/")
    write_fstart(suite)

    designs = y3_rows(
        [
            ("UI", "persona_id", "p1"),
            ("UI", "persona_code", "P1"),
            ("UI", "persona_name", "Studio Visitor"),
            ("UI", "persona_portfolio", "Home Work Services Contact"),
            ("UI", "base_url", base + "/"),
            ("UI", "work_url", base + "/work"),
            ("UI", "services_url", base + "/services"),
            ("UI", "about_url", base + "/about"),
            ("UI", "contact_url", base + "/contact"),
            ("UI", "blog_url", base + "/blog"),
            ("UI", "unknown_url", base + "/no-such-xyz-brahl"),
            ("UI", "api_host", base),
            ("UI", "ep_home", "/"),
            ("UI", "ep_favicon", "/favicon.ico"),
            ("UI", "ep_robots", "/robots.txt"),
            ("UI", "ep_unknown", "/no-such-xyz-brahl"),
            ("UI", "body_locator", "css=body"),
            ("UI", "btn_accept_cookies", "xpath=//button[contains(normalize-space(),'אשר הכל')]"),
            ("UI", "page_title_home", "CREATOP"),
            ("UI", "page_title_work", "תיק עבודות"),
            ("UI", "page_title_services", "שירותי"),
            ("UI", "page_title_contact", "צור קשר"),
            ("UI", "text_brand", "CREATOP"),
            ("UI", "text_home_nav", "בית"),
            ("UI", "text_work_nav", "פרויקטים"),
            ("UI", "text_services_nav", "שירות"),
            ("UI", "text_contact_nav", "צור קשר"),
            ("UI", "text_a11y", "נגישות"),
            ("UI", "text_work_heading", "פרויקטים"),
            ("UI", "text_services_heading", "מה אנחנו עושים"),
            ("UI", "text_about", "אלחנן אשואל"),
            ("UI", "text_contact", "בואו נדבר"),
            ("UI", "text_email", "stcreatop@gmail.com"),
            ("UI", "text_blog", "בלוג"),
            ("UI", "text_404", "הדף לא נמצא"),
            ("UI", "text_view_projects", "לצפייה בפרויקטים"),
        ]
    )
    write_csv(Y / suite / "y3Designs.csv", ["Type", "DataName", *[f"D{i}" for i in range(1, 10)]], designs)

    reuse = "PReuse_Creatop_Open"
    plans = [
        plan(reuse, "Open Edge, accept cookies, load Creatop", "Reuse", "site_loaded", "N"),
        plan("PCreatop_Smoke_Home", "Home CREATOP brand + nav", f"{suite};Smoke;Home;Landing", "home_ok"),
        plan("PCreatop_Smoke_Work", "Work portfolio projects", f"{suite};Smoke;Work", "work_ok"),
        plan("PCreatop_Smoke_Services", "Services מה אנחנו עושים", f"{suite};Smoke;Services", "services_ok"),
        plan("PCreatop_Smoke_About", "About Elhanan Ashuel", f"{suite};Smoke;About", "about_ok"),
        plan("PCreatop_Smoke_Contact", "Contact email + WhatsApp cue", f"{suite};Smoke;Contact", "contact_ok"),
        plan("PCreatop_Smoke_BrahlConclusion", "BRAHL conclusion — Creatop shell ready", f"{suite};Smoke;BRAHL;Conclusion", "brahl_conclusion"),
        plan("PCreatop_UI_NavRTL", "RTL nav בית פרויקטים שירות", f"{suite};UI;Nav;RTL", "nav_ok"),
        plan("PCreatop_UI_A11y", "Accessibility control visible", f"{suite};UI;A11y", "a11y_ok"),
        plan("PCreatop_UI_ContactEmail", "Contact shows studio email", f"{suite};UI;Contact", "email_ok"),
        plan("PCreatop_Edge_Unknown404", "Unknown path הדף לא נמצא", f"{suite};Edge;404", "edge_404"),
        plan("PCreatop_API_GetHome", "GET / 200", f"{suite};API;Home", "api_home"),
        plan("PCreatop_API_Favicon", "GET favicon 200", f"{suite};API;Favicon", "api_favicon"),
        plan("PCreatop_API_Robots", "GET robots 200", f"{suite};API;Robots", "api_robots"),
        plan("PCreatop_API_UnknownSpa", "GET unknown SPA 200", f"{suite};API;404", "api_unknown"),
        plan("PCreatop_Sec_HttpsHost", "HTTPS host", f"{suite};Security;Landing", "sec_https"),
        plan("PCreatop_Perf_HomeLoad", "Home load under 25s", f"{suite};Perf;Home", "perf_home"),
        plan("PCreatop_Manual_DarkMode", "HITL: light/dark mode toggle", f"{suite};Manual;Theme", "hitl_theme", "N"),
        plan("PCreatop_Manual_WhatsApp", "HITL: WhatsApp contact path", f"{suite};Manual;WhatsApp", "hitl_wa", "N"),
    ]
    write_csv(
        Y / suite / "y1Plans.csv",
        ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"],
        plans,
    )
    actions = [
        act(reuse, 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act(reuse, 2, "Home", "xUI", "xNavigate", "base_url"),
        act(reuse, 3, "Wait paint", "xTime", "xTimeWait", "6"),
        act("PCreatop_Smoke_Home", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_Home", 2, "Title", "xUI", "xGetTitle", "", "", "page_title_home"),
        act("PCreatop_Smoke_Home", 3, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PCreatop_Smoke_Home", 4, "Home nav", "xUI", "xGetText", "body_locator", "", "text_home_nav"),
        act("PCreatop_Smoke_Home", 5, "Contact", "xUI", "xGetText", "body_locator", "", "text_contact_nav"),
        act("PCreatop_Smoke_Work", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_Work", 2, "Work", "xUI", "xNavigate", "work_url"),
        act("PCreatop_Smoke_Work", 3, "Wait", "xTime", "xTimeWait", "5"),
        act("PCreatop_Smoke_Work", 4, "Title", "xUI", "xGetTitle", "", "", "page_title_work"),
        act("PCreatop_Smoke_Work", 5, "Projects", "xUI", "xGetText", "body_locator", "", "text_work_nav"),
        act("PCreatop_Smoke_Services", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_Services", 2, "Services", "xUI", "xNavigate", "services_url"),
        act("PCreatop_Smoke_Services", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PCreatop_Smoke_Services", 4, "Heading", "xUI", "xGetText", "body_locator", "", "text_services_heading"),
        act("PCreatop_Smoke_About", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_About", 2, "About", "xUI", "xNavigate", "about_url"),
        act("PCreatop_Smoke_About", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PCreatop_Smoke_About", 4, "Founder", "xUI", "xGetText", "body_locator", "", "text_about"),
        act("PCreatop_Smoke_Contact", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_Contact", 2, "Contact", "xUI", "xNavigate", "contact_url"),
        act("PCreatop_Smoke_Contact", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PCreatop_Smoke_Contact", 4, "Talk", "xUI", "xGetText", "body_locator", "", "text_contact"),
        act("PCreatop_Smoke_Contact", 5, "Email", "xUI", "xGetText", "body_locator", "", "text_email"),
        act("PCreatop_Smoke_BrahlConclusion", 1, "Open", "xReuse", reuse),
        act("PCreatop_Smoke_BrahlConclusion", 2, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PCreatop_Smoke_BrahlConclusion", 3, "API", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PCreatop_UI_NavRTL", 1, "Open", "xReuse", reuse),
        act("PCreatop_UI_NavRTL", 2, "Home", "xUI", "xGetText", "body_locator", "", "text_home_nav"),
        act("PCreatop_UI_NavRTL", 3, "Work", "xUI", "xGetText", "body_locator", "", "text_work_nav"),
        act("PCreatop_UI_NavRTL", 4, "Services", "xUI", "xGetText", "body_locator", "", "text_services_nav"),
        act("PCreatop_UI_A11y", 1, "Open", "xReuse", reuse),
        act("PCreatop_UI_A11y", 2, "A11y", "xUI", "xGetText", "body_locator", "", "text_a11y"),
        act("PCreatop_UI_ContactEmail", 1, "Open", "xReuse", reuse),
        act("PCreatop_UI_ContactEmail", 2, "Contact", "xUI", "xNavigate", "contact_url"),
        act("PCreatop_UI_ContactEmail", 3, "Wait", "xTime", "xTimeWait", "4"),
        act("PCreatop_UI_ContactEmail", 4, "Email", "xUI", "xGetText", "body_locator", "", "text_email"),
        act("PCreatop_Edge_Unknown404", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PCreatop_Edge_Unknown404", 2, "Unknown", "xUI", "xNavigate", "unknown_url"),
        act("PCreatop_Edge_Unknown404", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PCreatop_Edge_Unknown404", 4, "404", "xUI", "xGetText", "body_locator", "", "text_404"),
        act("PCreatop_API_GetHome", 1, "GET", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PCreatop_API_Favicon", 1, "GET", "xAPI", "xGet", "api_host;ep_favicon", "", "200"),
        act("PCreatop_API_Robots", 1, "GET", "xAPI", "xGet", "api_host;ep_robots", "", "200"),
        act("PCreatop_API_UnknownSpa", 1, "GET", "xAPI", "xGet", "api_host;ep_unknown", "", "200"),
        act("PCreatop_Sec_HttpsHost", 1, "Open", "xReuse", reuse),
        act("PCreatop_Sec_HttpsHost", 2, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PCreatop_Perf_HomeLoad", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PCreatop_Perf_HomeLoad", 2, "Start", "xUI", "xStartTimer"),
        act("PCreatop_Perf_HomeLoad", 3, "Nav", "xUI", "xNavigate", "base_url"),
        act("PCreatop_Perf_HomeLoad", 4, "Wait paint", "xTime", "xTimeWait", "5"),
        act("PCreatop_Perf_HomeLoad", 5, "Stop", "xUI", "xStopTimer", "elapsed"),
        act("PCreatop_Perf_HomeLoad", 6, "Budget", "xUI", "xAssertLessThan", "{{step:5}};25000"),
        act("PCreatop_Perf_HomeLoad", 7, "Alive", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PCreatop_Manual_DarkMode", 1, "Open", "xReuse", reuse, crit="N"),
        act("PCreatop_Manual_DarkMode", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_brand", "N"),
        act("PCreatop_Manual_WhatsApp", 1, "Open", "xReuse", reuse, crit="N"),
        act("PCreatop_Manual_WhatsApp", 2, "Contact", "xUI", "xNavigate", "contact_url", crit="N"),
        act("PCreatop_Manual_WhatsApp", 3, "Note", "xUI", "xGetText", "body_locator", "", "text_contact", "N"),
    ]
    write_csv(
        Y / suite / "y2Actions.csv",
        ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"],
        actions,
    )
    (Y / suite / "test plan.md").write_text(
        """# Test plan — Creatop

| Area | Profile | Plans |
|------|---------|-------|
| Home (cookies) | Smoke | PCreatop_Smoke_Home |
| Work / Services / About / Contact | Smoke | PCreatop_Smoke_* |
| RTL nav + a11y | UI | NavRTL, A11y |
| 404 Hebrew | Edge | הדף לא נמצא |
| Theme / WhatsApp | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/creatop.json
```
""",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# AppWars
# ---------------------------------------------------------------------------
def author_appwars() -> None:
    suite = "appwars"
    base = "https://appwars.base44.app"
    write_suite_json(suite, "AppWars", "AppWars tournament bracket — Smoke UI Edge API Security Perf", base + "/")
    write_fstart(suite)

    designs = y3_rows(
        [
            ("UI", "persona_id", "p1"),
            ("UI", "persona_code", "P1"),
            ("UI", "persona_name", "Tournament Competitor"),
            ("UI", "persona_portfolio", "Landing Login Support Legal"),
            ("UI", "base_url", base + "/"),
            ("UI", "login_url", base + "/login"),
            ("UI", "support_url", base + "/support"),
            ("UI", "privacy_url", base + "/privacy-policy"),
            ("UI", "terms_url", base + "/terms-and-conditions"),
            ("UI", "unknown_url", base + "/no-such-xyz-brahl"),
            ("UI", "api_host", base),
            ("UI", "ep_home", "/"),
            ("UI", "ep_favicon", "/favicon.ico"),
            ("UI", "ep_robots", "/robots.txt"),
            ("UI", "ep_unknown", "/no-such-xyz-brahl"),
            ("UI", "body_locator", "css=body"),
            ("UI", "btn_enter", "xpath=//button[contains(normalize-space(),'Enter the Arena')]"),
            ("UI", "page_title_home", "AppWars"),
            ("UI", "page_title_support", "Support"),
            ("UI", "page_title_privacy", "Privacy"),
            ("UI", "page_title_terms", "Terms"),
            ("UI", "text_brand", "AppWars"),
            ("UI", "text_build_battle", "Build. Battle."),
            ("UI", "text_crowned", "Get crowned."),
            ("UI", "text_enter", "Enter the Arena"),
            ("UI", "text_pressure", "Build under pressure"),
            ("UI", "text_community", "Community-judged"),
            ("UI", "text_prizes", "Win real prizes"),
            ("UI", "text_welcome", "Welcome to AppWars"),
            ("UI", "text_google", "Continue with Google"),
            ("UI", "text_support", "We're here to help"),
            ("UI", "text_privacy", "Privacy Policy"),
            ("UI", "text_terms", "Terms and Conditions"),
            ("UI", "text_soft404", "Build. Battle."),
        ]
    )
    write_csv(Y / suite / "y3Designs.csv", ["Type", "DataName", *[f"D{i}" for i in range(1, 10)]], designs)

    reuse = "PReuse_AppWars_Open"
    plans = [
        plan(reuse, "Open Edge and load AppWars", "Reuse", "site_loaded", "N"),
        plan("PAppWars_Smoke_Home", "Landing Build Battle crowned", f"{suite};Smoke;Home;Landing", "home_ok"),
        plan("PAppWars_Smoke_EnterLogin", "Enter Arena gates to login", f"{suite};Smoke;Auth;Arena", "enter_ok"),
        plan("PAppWars_Smoke_Support", "Support help page", f"{suite};Smoke;Support", "support_ok"),
        plan("PAppWars_Smoke_Privacy", "Privacy policy", f"{suite};Smoke;Privacy", "privacy_ok"),
        plan("PAppWars_Smoke_Terms", "Terms and Conditions", f"{suite};Smoke;Terms", "terms_ok"),
        plan("PAppWars_Smoke_BrahlConclusion", "BRAHL conclusion — AppWars shell ready", f"{suite};Smoke;BRAHL;Conclusion", "brahl_conclusion"),
        plan("PAppWars_UI_ValueProps", "Pressure / community / prizes", f"{suite};UI;Landing", "props_ok"),
        plan("PAppWars_UI_LoginGoogle", "Login Continue with Google", f"{suite};UI;Auth", "google_ok"),
        plan("PAppWars_Edge_Soft404", "Unknown path soft-falls to landing (A1 soft 404)", f"{suite};Edge;404", "edge_soft404"),
        plan("PAppWars_API_GetHome", "GET / 200", f"{suite};API;Home", "api_home"),
        plan("PAppWars_API_Favicon", "GET favicon 200", f"{suite};API;Favicon", "api_favicon"),
        plan("PAppWars_API_Robots", "GET robots 200", f"{suite};API;Robots", "api_robots"),
        plan("PAppWars_API_UnknownSpa", "GET unknown SPA 200", f"{suite};API;404", "api_unknown"),
        plan("PAppWars_Sec_HttpsHost", "HTTPS host", f"{suite};Security;Landing", "sec_https"),
        plan("PAppWars_Perf_HomeLoad", "Home load under 15s", f"{suite};Perf;Home", "perf_home"),
        plan("PAppWars_Manual_Tournament", "HITL: join tournament bracket", f"{suite};Manual;Tournament", "hitl_tourney", "N"),
        plan("PAppWars_Manual_Vote", "HITL: community vote matchup", f"{suite};Manual;Vote", "hitl_vote", "N"),
    ]
    write_csv(
        Y / suite / "y1Plans.csv",
        ["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output", "CreatedBy", "CreatedAt"],
        plans,
    )
    actions = [
        act(reuse, 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act(reuse, 2, "Home", "xUI", "xNavigate", "base_url"),
        act(reuse, 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_Smoke_Home", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_Home", 2, "Title", "xUI", "xGetTitle", "", "", "page_title_home"),
        act("PAppWars_Smoke_Home", 3, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PAppWars_Smoke_Home", 4, "Battle", "xUI", "xGetText", "body_locator", "", "text_build_battle"),
        act("PAppWars_Smoke_Home", 5, "Crowned", "xUI", "xGetText", "body_locator", "", "text_crowned"),
        act("PAppWars_Smoke_Home", 6, "Enter", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PAppWars_Smoke_EnterLogin", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_EnterLogin", 2, "Click enter", "xUI", "xClick", "btn_enter"),
        act("PAppWars_Smoke_EnterLogin", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_Smoke_EnterLogin", 4, "Welcome", "xUI", "xGetText", "body_locator", "", "text_welcome"),
        act("PAppWars_Smoke_EnterLogin", 5, "Google", "xUI", "xGetText", "body_locator", "", "text_google"),
        act("PAppWars_Smoke_Support", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_Support", 2, "Support", "xUI", "xNavigate", "support_url"),
        act("PAppWars_Smoke_Support", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_Smoke_Support", 4, "Help", "xUI", "xGetText", "body_locator", "", "text_support"),
        act("PAppWars_Smoke_Privacy", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_Privacy", 2, "Privacy", "xUI", "xNavigate", "privacy_url"),
        act("PAppWars_Smoke_Privacy", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_Smoke_Privacy", 4, "Policy", "xUI", "xGetText", "body_locator", "", "text_privacy"),
        act("PAppWars_Smoke_Terms", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_Terms", 2, "Terms", "xUI", "xNavigate", "terms_url"),
        act("PAppWars_Smoke_Terms", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_Smoke_Terms", 4, "Legal", "xUI", "xGetText", "body_locator", "", "text_terms"),
        act("PAppWars_Smoke_BrahlConclusion", 1, "Open", "xReuse", reuse),
        act("PAppWars_Smoke_BrahlConclusion", 2, "Battle", "xUI", "xGetText", "body_locator", "", "text_build_battle"),
        act("PAppWars_Smoke_BrahlConclusion", 3, "API", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PAppWars_UI_ValueProps", 1, "Open", "xReuse", reuse),
        act("PAppWars_UI_ValueProps", 2, "Pressure", "xUI", "xGetText", "body_locator", "", "text_pressure"),
        act("PAppWars_UI_ValueProps", 3, "Community", "xUI", "xGetText", "body_locator", "", "text_community"),
        act("PAppWars_UI_ValueProps", 4, "Prizes", "xUI", "xGetText", "body_locator", "", "text_prizes"),
        act("PAppWars_UI_LoginGoogle", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PAppWars_UI_LoginGoogle", 2, "Login", "xUI", "xNavigate", "login_url"),
        act("PAppWars_UI_LoginGoogle", 3, "Wait", "xTime", "xTimeWait", "3"),
        act("PAppWars_UI_LoginGoogle", 4, "Google", "xUI", "xGetText", "body_locator", "", "text_google"),
        act("PAppWars_Edge_Soft404", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PAppWars_Edge_Soft404", 2, "Unknown", "xUI", "xNavigate", "unknown_url"),
        act("PAppWars_Edge_Soft404", 3, "Wait", "xTime", "xTimeWait", "2"),
        act("PAppWars_Edge_Soft404", 4, "Still landing", "xUI", "xGetText", "body_locator", "", "text_soft404"),
        act("PAppWars_API_GetHome", 1, "GET", "xAPI", "xGet", "api_host;ep_home", "", "200"),
        act("PAppWars_API_Favicon", 1, "GET", "xAPI", "xGet", "api_host;ep_favicon", "", "200"),
        act("PAppWars_API_Robots", 1, "GET", "xAPI", "xGet", "api_host;ep_robots", "", "200"),
        act("PAppWars_API_UnknownSpa", 1, "GET", "xAPI", "xGet", "api_host;ep_unknown", "", "200"),
        act("PAppWars_Sec_HttpsHost", 1, "Open", "xReuse", reuse),
        act("PAppWars_Sec_HttpsHost", 2, "Brand", "xUI", "xGetText", "body_locator", "", "text_brand"),
        act("PAppWars_Perf_HomeLoad", 1, "Open Edge", "xUI", "xOpenBrowser", "edge"),
        act("PAppWars_Perf_HomeLoad", 2, "Start", "xUI", "xStartTimer"),
        act("PAppWars_Perf_HomeLoad", 3, "Nav", "xUI", "xNavigate", "base_url"),
        act("PAppWars_Perf_HomeLoad", 4, "Stop", "xUI", "xStopTimer", "elapsed"),
        act("PAppWars_Perf_HomeLoad", 5, "Budget", "xUI", "xAssertLessThan", "{{step:4}};15000"),
        act("PAppWars_Perf_HomeLoad", 6, "Alive", "xUI", "xGetText", "body_locator", "", "text_enter"),
        act("PAppWars_Manual_Tournament", 1, "Open", "xReuse", reuse, crit="N"),
        act("PAppWars_Manual_Tournament", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_enter", "N"),
        act("PAppWars_Manual_Vote", 1, "Open", "xReuse", reuse, crit="N"),
        act("PAppWars_Manual_Vote", 2, "Note", "xUI", "xGetText", "body_locator", "", "text_community", "N"),
    ]
    write_csv(
        Y / suite / "y2Actions.csv",
        ["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"],
        actions,
    )
    (Y / suite / "test plan.md").write_text(
        """# Test plan — AppWars

| Area | Profile | Plans |
|------|---------|-------|
| Landing | Smoke | Home |
| Enter → Login | Smoke + UI | EnterLogin, LoginGoogle |
| Support / Privacy / Terms | Smoke | legal pages |
| Soft 404 (A1) | Edge | unknown still shows landing |
| Tournament / vote | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/appwars.json
```
""",
        encoding="utf-8",
    )


def main() -> None:
    author_life_leveled()
    author_space_planner()
    author_haunted_castle()
    author_creatop()
    author_appwars()
    print("Wave 1 suites authored:")
    for s in ["life_leveled", "space_planner", "haunted_castle", "creatop", "appwars"]:
        print(" -", s, "→", Y / s)


if __name__ == "__main__":
    main()
