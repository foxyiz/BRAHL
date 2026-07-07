"""Generate persona-based yPAD rows (D1–D9 = P1–P9). Run from KK/: python u/gen_persona_ypad.py"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from _paths import KK_ROOT, SUITE_QOA_WEB

ROOT = SUITE_QOA_WEB
DATA_DIR = KK_ROOT / "Docs" / "test-user-data"
BASE = "http://127.0.0.1:8765"
APP = f"{BASE}/app"


def load_personas_from_docs() -> list[tuple]:
    idx = json.loads((DATA_DIR / "index.json").read_text(encoding="utf-8"))
    out: list[tuple] = []
    for entry in idx.get("personas", []):
        path = DATA_DIR / entry["file"]
        p = json.loads(path.read_text(encoding="utf-8"))
        allowed = p.get("allowed_avatars") or []
        out.append(
            (
                entry["ypad_design_column"],
                p["id"],
                p["code"],
                p["name"],
                p.get("default_avatar", "client"),
                "consultant" in allowed,
                "client" in allowed,
            )
        )
    return out


PERSONAS = load_personas_from_docs()
COLS = [p[0] for p in PERSONAS]

_idx = json.loads((DATA_DIR / "index.json").read_text(encoding="utf-8"))
PROFILE_URLS: dict[str, str] = {}
for entry in _idx.get("personas", []):
    p = json.loads((DATA_DIR / entry["file"]).read_text(encoding="utf-8"))
    col = entry["ypad_design_column"]
    PROFILE_URLS[col] = p.get("profile_url") or (
        f"{APP}?reset=1&profile={p['id']}&suite=qoa_web&demo=1"
    )


def col_vals(fn):
    return {c: fn(p) for c, p in zip(COLS, PERSONAS)}


rows: list[dict[str, str]] = []


def add(typ: str, name: str, vals: dict[str, str]) -> None:
    rows.append({"Type": typ, "DataName": name, **{c: vals.get(c, "") for c in COLS}})


add("UI", "profile_url", {c: PROFILE_URLS[c] for c in COLS})
add("UI", "persona_id", col_vals(lambda p: p[1]))
add("UI", "persona_code", col_vals(lambda p: p[2]))
add("UI", "persona_name", col_vals(lambda p: p[3]))
add("UI", "default_avatar", col_vals(lambda p: p[4]))
add("UI", "can_switch_client", col_vals(lambda p: "Y" if p[6] else "N"))
add("UI", "can_switch_hitl", col_vals(lambda p: "Y" if p[5] else "N"))
add("UI", "signin_url", col_vals(lambda p: f"{BASE}/signin"))
add(
    "UI",
    "signin_card_btn",
    col_vals(lambda p: f'css=[data-profile-id="{p[1]}"] .signin-select'),
)
add("UI", "persona_tasks_source", col_vals(lambda _p: "Docs/test-user-data/"))

SHARED = {
    "fresh_url": f"{APP}?reset=1&demo=1",
    "base_url": f"{APP}/?demo=1",
    "body_locator": "css=body",
    "app_title_locator": "css=#app-title",
    "tagline_locator": "css=.tagline",
    "nav_build_btn": "css=button[data-phase='build']",
    "nav_run_btn": "css=button[data-phase='run']",
    "nav_analyze_btn": "css=button[data-phase='analyze']",
    "nav_heal_btn": "css=button[data-phase='heal']",
    "nav_loop_btn": "css=button[data-phase='loop']",
    "nav_brahl_btn": "css=button[data-phase='brahl']",
    "nav_cost_btn": "css=button[data-phase='cost']",
    "avatar_client_bar_btn": "css=.avatar-btn[data-avatar='client']",
    "avatar_hitl_bar_btn": "css=.avatar-btn[data-avatar='consultant']",
    "topbar_project_selected_locator": "css=#topbar-project-select option:checked",
    "topbar_project_label_locator": "css=.topbar-project-label",
    "build_panel_title_locator": "css=#build-panel-title",
    "ai_toggle_label_locator": "css=#ai-toggle-label",
    "chat_input_locator": "css=#chat-input",
    "budget_block_locator": "css=.budget-block h3",
    "build_refine_summary_locator": "css=#build-refine-details summary",
    "build_checklist_locator": "css=#build-checklist",
    "run_heading_locator": "css=#panel-run h2",
    "analyze_heading_locator": "css=#panel-analyze h2",
    "heal_heading_locator": "css=#panel-heal h2",
    "loop_heading_locator": "css=#panel-loop h2",
    "brahl_heading_locator": "css=#panel-brahl h2",
    "run_scope_locator": "css=#run-project-scope",
    "analyze_scope_locator": "css=#analyze-project-scope",
    "btn_refresh_locator": "css=#btn-refresh-runs",
    "btn_join_hitl_locator": "css=#btn-join-hitl",
    "health_pill_locator": "css=#health-pill",
    "footer_version_locator": "css=#footer-version",
    "phase_progress_locator": "css=#phase-progress",
    "btn_shrink_locator": "css=#btn-shrink-plans",
    "btn_run_locator": "css=#btn-run",
    "config_label_locator": "css=label[for='config-select']",
    "run_suite_display_locator": "css=#run-suite-display",
    "brahl_report_list_locator": "css=#brahl-report-list",
    "brahl_chat_input_locator": "css=#brahl-chat-input",
    "btn_link_report_locator": "css=#btn-link-run-report",
    "consultant_tier_banner_locator": "css=#consultant-tier-banner",
    "profile_chip_code_locator": "css=#profile-chip-code",
    "profile_chip_name_locator": "css=#profile-chip-name",
    "ypad_explorer_locator": "css=.ypad-tab[data-ypad-tab='plans']",
    "build_consultant_panel_locator": "css=#build-consultant-panel .section-sub",
    "client_manual_build_locator": "css=#client-manual-build",
    "btn_new_project_locator": "css=#client-empty-add",
    "app_title_expected": "BRAHL Web — f(x,y)=z",
    "topbar_suite_expected": "qoa_web — http://127.0.0.1:8765/",
    "build_title_client_expected": "Build — qoa_web",
    "build_title_hitl_expected": "Build — qoa_web (QA Hunter)",
    "join_btn_expected": "Join as QA Hunter",
    "ai_off_label_expected": "AI off (profile)",
    "senior_banner_expected": "Senior QA Hunter — mentor-level deliverables, hybrid Automation + AI reports, yPAD shrink/restore guidance.",
    "run_heading_expected": "Run — FoXYiZ fEngine2",
    "analyze_heading_expected": "Analyze — z/",
    "heal_shrink_expected": "Shrink to failures (Loop 2 prep)",
    "loop_heading_expected": "Loop — BRAHL cycle (FoXYiZ)",
    "brahl_heading_expected": "BRAHL — cycle report",
    "consultant_panel_heading_expected": "QA Hunter workspace",
    "add_challenge_btn_expected": "Add challenge to arena",
    "api_base_url": BASE,
    "api_health_endpoint": "/api/health",
    "api_signin_endpoint": "/signin",
    "api_profiles_js_endpoint": "/assets/profiles.js",
    "api_projects_endpoint": "/api/projects?role=client",
    "api_projects_consultant_endpoint": "/api/projects?role=consultant",
    "api_suites_endpoint": "/api/suites",
    "api_runs_endpoint": "/api/runs?suite=qoa_web",
    "api_version_endpoint": "/api/version",
    "api_index_endpoint": "/",
    "api_css_endpoint": "/assets/styles.css",
    "api_js_endpoint": "/assets/app.js",
    "payload_job_path": "y/qoa_web/payload_job.json",
    "payload_context_path": "y/qoa_web/payload_context.json",
    "payload_chat_path": "y/qoa_web/payload_chat.json",
}

for key, val in SHARED.items():
    add("UI", key, {c: val for c in COLS})

designs_path = ROOT / "y3Designs.csv"
with designs_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["Type", "DataName", *COLS])
    w.writeheader()
    w.writerows(rows)

# --- Plans ---
plans = [
    ("PReuse_qoa_web_OpenSite", "Open browser and navigate to BRAHL Web", "D1", "N", "Reuse", "site_loaded"),
    ("PReuse_PersonaReady", "Sign in test persona via profile URL", "D1", "N", "Reuse;Persona", "persona_ready"),
    ("PReuse_qoa_web_ClientReady", "Persona ready as Client with qoa_web project", "D1", "N", "Reuse;Client", "client_ready"),
    ("PReuse_qoa_web_HitlReady", "Persona ready as HITL with qoa_web project", "D3", "N", "Reuse;HITL", "hitl_ready"),
    ("PWeb_Signin_Page", "Sign-in page lists test profiles", "D1", "Y", "qoa_web;Signin;Persona", "signin_ok"),
    ("PWeb_Profile_Chip", "Profile chip shows persona code in top bar", "D1", "Y", "qoa_web;Persona;Shell", "profile_chip_ok"),
    ("PWeb_Nav_CostTab", "Cost meter tab visible in phase nav", "D1", "Y", "qoa_web;Cost;Navigation", "cost_nav_ok"),
    ("PWeb_OpenHome", "Open BRAHL Web home page", "D1", "Y", "qoa_web;Smoke;Landing", "home_ok"),
    ("PWeb_VerifyTitle", "Verify app title element", "D1", "Y", "qoa_web;Smoke;Landing", "title_ok"),
    ("PWeb_Nav_SixPhases", "Verify phase nav buttons", "D1", "Y", "qoa_web;Smoke;Navigation", "nav_ok"),
    ("PWeb_Topbar_Project", "Topbar project dropdown populated", "D1", "Y", "qoa_web;Build;Project", "topbar_ok"),
    ("PWeb_Panel_Build", "Build panel with project title", "D1", "Y", "qoa_web;Smoke;Build", "build_ok"),
    ("PWeb_Build_ChatInput", "Build chat input for client persona", "D1", "Y", "qoa_web;Build;Client", "chat_ok"),
    ("PWeb_Build_Budget", "Budget block for client persona", "D1", "Y", "qoa_web;Build;Client", "budget_ok"),
    ("PWeb_Hitl_Avatar_Switch", "Dual persona switches Client to HITL", "D2", "Y", "qoa_web;HITL;Persona;P2", "hitl_switch_ok"),
    ("PWeb_Hitl_JoinButton", "HITL join button on unified Build", "D3", "Y", "qoa_web;HITL;Build", "hitl_join_ok"),
    ("PWeb_Hitl_TierBanner", "Senior consultant tier banner", "D4", "Y", "qoa_web;HITL;Persona;P4", "tier_banner_ok"),
    ("PWeb_Manual_AiLocked", "Non-tech persona AI toggle locked off", "D5", "Y", "qoa_web;Persona;P5;AI", "ai_locked_ok"),
    ("PWeb_Power_YpadExplorer", "Power client sees yPAD explorer", "D7", "Y", "qoa_web;Persona;P7;yPAD", "ypad_ok"),
    ("PWeb_Panel_Run", "Run panel scoped to project", "D1", "Y", "qoa_web;Smoke;Run", "run_panel_ok"),
    ("PWeb_Panel_Analyze", "Analyze panel scoped to project", "D1", "Y", "qoa_web;Smoke;Analyze", "analyze_panel_ok"),
    ("PWeb_Panel_Heal", "Heal panel with shrink controls", "D1", "Y", "qoa_web;Smoke;Heal", "heal_panel_ok"),
    ("PWeb_Panel_Loop", "Loop panel controls", "D1", "Y", "qoa_web;Smoke;Loop", "loop_panel_ok"),
    ("PWeb_Panel_Brahl", "BRAHL reports panel", "D1", "Y", "qoa_web;Smoke;BRAHL", "brahl_panel_ok"),
    ("PWeb_Footer_Health", "Footer health pill", "D1", "Y", "qoa_web;Smoke;Shell", "footer_ok"),
    ("PAPI_Health", "GET api health", "D1", "Y", "qoa_web;Smoke;API", "health_ok"),
    ("PAPI_Signin", "GET sign-in page", "D1", "Y", "qoa_web;API;Signin", "signin_api_ok"),
    ("PAPI_ProfilesJs", "GET profiles.js asset", "D1", "Y", "qoa_web;API;Persona", "profiles_js_ok"),
    ("PAPI_Suites", "GET api suites", "D1", "Y", "qoa_web;API", "suites_ok"),
    ("PAPI_ProjectsConsultant", "GET consultant projects", "D3", "Y", "qoa_web;API;HITL", "projects_consultant_ok"),
    ("PPersona_P1_Journey", "P1 client MVP journey Build tab", "D1", "Y", "Persona;P1;Journey", "p1_ok"),
    ("PPersona_P2_Journey", "P2 dual role profile chip and avatars", "D2", "Y", "Persona;P2;Journey", "p2_ok"),
    ("PPersona_P3_Journey", "P3 consultant HITL workspace", "D3", "Y", "Persona;P3;Journey", "p3_ok"),
    ("PPersona_P4_Journey", "P4 senior consultant tier", "D4", "Y", "Persona;P4;Journey", "p4_ok"),
    ("PPersona_P5_Journey", "P5 manual client no AI", "D5", "Y", "Persona;P5;Journey", "p5_ok"),
    ("PPersona_P6_Journey", "P6 admin dual avatar access", "D6", "Y", "Persona;P6;Journey", "p6_ok"),
    ("PPersona_P7_Journey", "P7 power client yPAD", "D7", "Y", "Persona;P7;Journey", "p7_ok"),
    ("PPersona_P8_Journey", "P8 bug-bounty HITL join", "D8", "Y", "Persona;P8;Journey", "p8_ok"),
    ("PPersona_P9_Journey", "P9 first-time user NUX empty state", "D9", "Y", "Persona;P9;NUX;NewUser", "p9_ok"),
    ("PWeb_NUX_EmptyBuild", "P9 empty Build add-project prompt", "D9", "Y", "qoa_web;NUX;Build", "nux_empty_ok"),
]

actions: list[tuple] = [
    ("PReuse_qoa_web_OpenSite", 1, "Open browser", "xUI", "xOpenBrowser", "edge", "", "", "y"),
    ("PReuse_qoa_web_OpenSite", 2, "Navigate home", "xUI", "xNavigate", "base_url", "", "", "y"),
    ("PReuse_PersonaReady", 1, "Open browser", "xReuse", "PReuse_qoa_web_OpenSite", "", "", "", "y"),
    ("PReuse_PersonaReady", 2, "Load persona profile URL", "xUI", "xNavigate", "profile_url", "", "", "y"),
    ("PReuse_PersonaReady", 3, "Verify profile chip code", "xUI", "xGetText", "profile_chip_code_locator", "", "", "y"),
    ("PReuse_qoa_web_ClientReady", 1, "Persona ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PReuse_qoa_web_ClientReady", 2, "Click Client if needed", "xUI", "xClick", "avatar_client_bar_btn", "", "", "y"),
    ("PReuse_qoa_web_ClientReady", 3, "Verify topbar challenge label", "xUI", "xGetText", "topbar_project_label_locator", "", "My challenge", "y"),
    ("PReuse_qoa_web_HitlReady", 1, "Persona ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PReuse_qoa_web_HitlReady", 2, "Click HITL avatar", "xUI", "xClick", "avatar_hitl_bar_btn", "", "", "y"),
    ("PReuse_qoa_web_HitlReady", 3, "Verify Build QA Hunter title", "xUI", "xGetText", "build_panel_title_locator", "", "build_title_hitl_expected", "y"),
    ("PWeb_Signin_Page", 1, "Open browser", "xReuse", "PReuse_qoa_web_OpenSite", "", "", "", "y"),
    ("PWeb_Signin_Page", 2, "Navigate sign-in", "xUI", "xNavigate", "signin_url", "", "", "y"),
    ("PWeb_Signin_Page", 3, "Verify sign-in grid", "xUI", "xGetText", "body_locator", "", "", "y"),
    ("PWeb_Profile_Chip", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Profile_Chip", 2, "Verify profile code", "xUI", "xGetText", "profile_chip_code_locator", "", "", "y"),
    ("PWeb_Nav_CostTab", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Nav_CostTab", 2, "Verify cost tab", "xUI", "xGetText", "nav_cost_btn", "", "$", "y"),
    ("PWeb_OpenHome", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_OpenHome", 2, "Verify body", "xUI", "xGetText", "body_locator", "", "", "y"),
    ("PWeb_VerifyTitle", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_VerifyTitle", 2, "Verify title", "xUI", "xGetText", "app_title_locator", "", "app_title_expected", "y"),
    ("PWeb_Nav_SixPhases", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Nav_SixPhases", 2, "Build nav", "xUI", "xGetText", "nav_build_btn", "", "Build", "y"),
    ("PWeb_Nav_SixPhases", 3, "Run nav", "xUI", "xGetText", "nav_run_btn", "", "Run", "y"),
    ("PWeb_Nav_SixPhases", 4, "Analyze nav", "xUI", "xGetText", "nav_analyze_btn", "", "Analyze", "y"),
    ("PWeb_Topbar_Project", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Topbar_Project", 2, "Verify project dropdown", "xUI", "xGetText", "topbar_project_selected_locator", "", "topbar_suite_expected", "y"),
    ("PWeb_Panel_Build", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Build", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PWeb_Panel_Build", 3, "Verify Build title", "xUI", "xGetText", "build_panel_title_locator", "", "build_title_client_expected", "y"),
    ("PWeb_Build_ChatInput", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Build_ChatInput", 2, "Verify chat input", "xUI", "xGetText", "chat_input_locator", "", "", "y"),
    ("PWeb_Build_Budget", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Build_Budget", 2, "Open refine section", "xUI", "xClick", "build_refine_summary_locator", "", "", "y"),
    ("PWeb_Build_Budget", 3, "Verify budget", "xUI", "xGetText", "budget_block_locator", "", "Budget", "y"),
    ("PWeb_Hitl_Avatar_Switch", 1, "P2 persona ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PWeb_Hitl_Avatar_Switch", 2, "Click HITL avatar", "xUI", "xClick", "avatar_hitl_bar_btn", "", "", "y"),
    ("PWeb_Hitl_Avatar_Switch", 3, "Verify QA Hunter Build title", "xUI", "xGetText", "build_panel_title_locator", "", "build_title_hitl_expected", "y"),
    ("PWeb_Hitl_Avatar_Switch", 4, "Verify join button", "xUI", "xGetText", "btn_join_hitl_locator", "", "join_btn_expected", "y"),
    ("PWeb_Hitl_JoinButton", 1, "HITL ready", "xReuse", "PReuse_qoa_web_HitlReady", "", "", "", "y"),
    ("PWeb_Hitl_JoinButton", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PWeb_Hitl_JoinButton", 3, "Verify join button", "xUI", "xGetText", "btn_join_hitl_locator", "", "join_btn_expected", "y"),
    ("PWeb_Hitl_TierBanner", 1, "P4 persona", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PWeb_Hitl_TierBanner", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PWeb_Hitl_TierBanner", 3, "Verify senior banner", "xUI", "xGetText", "consultant_tier_banner_locator", "", "senior_banner_expected", "y"),
    ("PWeb_Manual_AiLocked", 1, "P5 persona", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PWeb_Manual_AiLocked", 2, "Verify AI off label", "xUI", "xGetText", "ai_toggle_label_locator", "", "ai_off_label_expected", "y"),
    ("PWeb_Power_YpadExplorer", 1, "P7 persona", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PWeb_Power_YpadExplorer", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PWeb_Power_YpadExplorer", 3, "Verify yPAD explorer", "xUI", "xGetText", "ypad_explorer_locator", "", "Y Plans", "y"),
    ("PWeb_Panel_Run", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Run", 2, "Click Run", "xUI", "xClick", "nav_run_btn", "", "", "y"),
    ("PWeb_Panel_Run", 3, "Verify Run heading", "xUI", "xGetText", "run_heading_locator", "", "run_heading_expected", "y"),
    ("PWeb_Panel_Analyze", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Analyze", 2, "Click Analyze", "xUI", "xClick", "nav_analyze_btn", "", "", "y"),
    ("PWeb_Panel_Analyze", 3, "Verify Analyze heading", "xUI", "xGetText", "analyze_heading_locator", "", "analyze_heading_expected", "y"),
    ("PWeb_Panel_Heal", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Heal", 2, "Click Heal", "xUI", "xClick", "nav_heal_btn", "", "", "y"),
    ("PWeb_Panel_Heal", 3, "Verify shrink button", "xUI", "xGetText", "btn_shrink_locator", "", "heal_shrink_expected", "y"),
    ("PWeb_Panel_Loop", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Loop", 2, "Click Loop", "xUI", "xClick", "nav_loop_btn", "", "", "y"),
    ("PWeb_Panel_Loop", 3, "Verify Loop heading", "xUI", "xGetText", "loop_heading_locator", "", "loop_heading_expected", "y"),
    ("PWeb_Panel_Brahl", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Panel_Brahl", 2, "Click BRAHL", "xUI", "xClick", "nav_brahl_btn", "", "", "y"),
    ("PWeb_Panel_Brahl", 3, "Verify BRAHL heading", "xUI", "xGetText", "brahl_heading_locator", "", "brahl_heading_expected", "y"),
    ("PWeb_Footer_Health", 1, "Client ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PWeb_Footer_Health", 2, "Verify health pill", "xUI", "xGetText", "health_pill_locator", "", "ok", "y"),
    ("PAPI_Health", 1, "GET health", "xAPI", "xGet", "api_base_url;api_health_endpoint", "", "200", "y"),
    ("PAPI_Signin", 1, "GET signin", "xAPI", "xGet", "api_base_url;api_signin_endpoint", "", "200", "y"),
    ("PAPI_ProfilesJs", 1, "GET profiles.js", "xAPI", "xGet", "api_base_url;api_profiles_js_endpoint", "", "200", "y"),
    ("PAPI_Suites", 1, "GET suites", "xAPI", "xGet", "api_base_url;api_suites_endpoint", "", "200", "y"),
    ("PAPI_ProjectsConsultant", 1, "GET consultant projects", "xAPI", "xGet", "api_base_url;api_projects_consultant_endpoint", "", "200", "y"),
    ("PPersona_P1_Journey", 1, "P1 ready", "xReuse", "PReuse_qoa_web_ClientReady", "", "", "", "y"),
    ("PPersona_P1_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P1_Journey", 3, "Verify P1 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P1_Journey", 4, "Open refine section", "xUI", "xClick", "build_refine_summary_locator", "", "", "y"),
    ("PPersona_P1_Journey", 5, "Verify budget", "xUI", "xGetText", "budget_block_locator", "", "Budget", "y"),
    ("PPersona_P2_Journey", 1, "P2 ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P2_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P2_Journey", 3, "Verify P2 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P2_Journey", 4, "Click HITL", "xUI", "xClick", "avatar_hitl_bar_btn", "", "", "y"),
    ("PPersona_P2_Journey", 5, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PPersona_P2_Journey", 6, "Verify QA Hunter panel", "xUI", "xGetText", "build_consultant_panel_locator", "", "consultant_panel_heading_expected", "y"),
    ("PPersona_P3_Journey", 1, "P3 HITL ready", "xReuse", "PReuse_qoa_web_HitlReady", "", "", "", "y"),
    ("PPersona_P3_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P3_Journey", 3, "Verify P3 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P3_Journey", 4, "Verify join", "xUI", "xGetText", "btn_join_hitl_locator", "", "join_btn_expected", "y"),
    ("PPersona_P4_Journey", 1, "P4 ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P4_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P4_Journey", 3, "Verify P4 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P4_Journey", 4, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PPersona_P4_Journey", 5, "Verify senior banner", "xUI", "xGetText", "consultant_tier_banner_locator", "", "senior_banner_expected", "y"),
    ("PPersona_P5_Journey", 1, "P5 ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P5_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P5_Journey", 3, "Verify P5 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P5_Journey", 4, "Verify AI locked", "xUI", "xGetText", "ai_toggle_label_locator", "", "ai_off_label_expected", "y"),
    ("PPersona_P6_Journey", 1, "P6 ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P6_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P6_Journey", 3, "Verify P6 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P6_Journey", 4, "Verify dual HITL click", "xUI", "xClick", "avatar_hitl_bar_btn", "", "", "y"),
    ("PPersona_P7_Journey", 1, "P7 ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P7_Journey", 2, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P7_Journey", 3, "Verify P7 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P7_Journey", 4, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PPersona_P7_Journey", 5, "Verify yPAD", "xUI", "xGetText", "ypad_explorer_locator", "", "Y Plans", "y"),
    ("PPersona_P8_Journey", 1, "P8 persona ready", "xReuse", "PReuse_PersonaReady", "", "", "", "y"),
    ("PPersona_P8_Journey", 2, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PPersona_P8_Journey", 3, "Wait for profile", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P8_Journey", 4, "Verify P8 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P8_Journey", 5, "Verify join", "xUI", "xGetText", "btn_join_hitl_locator", "", "join_btn_expected", "y"),
    ("PPersona_P9_Journey", 1, "Load P9 profile URL", "xUI", "xNavigate", "profile_url", "", "", "y"),
    ("PPersona_P9_Journey", 2, "Wait for init", "xTime", "xTimeWait", "2", "", "", "y"),
    ("PPersona_P9_Journey", 3, "Verify P9 chip", "xUI", "xGetText", "profile_chip_code_locator", "", "persona_code", "y"),
    ("PPersona_P9_Journey", 4, "Click Build", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PPersona_P9_Journey", 5, "Verify add-challenge affordance", "xUI", "xGetText", "btn_new_project_locator", "", "add_challenge_btn_expected", "y"),
    ("PWeb_NUX_EmptyBuild", 1, "P9 profile loaded", "xReuse", "PPersona_P9_Journey", "", "", "", "y"),
    ("PWeb_NUX_EmptyBuild", 2, "Click Build tab", "xUI", "xClick", "nav_build_btn", "", "", "y"),
    ("PWeb_NUX_EmptyBuild", 3, "Verify add-challenge button", "xUI", "xGetText", "btn_new_project_locator", "", "add_challenge_btn_expected", "y"),
]

plans_path = ROOT / "y1Plans.csv"
with plans_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output"])
    w.writerows(plans)

actions_path = ROOT / "y2Actions.csv"
with actions_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["PlanId", "StepId", "StepInfo", "ActionType", "ActionName", "Input", "Output", "Expected", "Critical"])
    w.writerows(actions)

print(f"Wrote {designs_path.name}: {len(rows)} design rows, {len(COLS)} persona columns")
print(f"Wrote {plans_path.name}: {len(plans)} plans")
print(f"Wrote {actions_path.name}: {len(actions)} action steps")
