#!/usr/bin/env python3
"""Generate qoa_web journey regression yPAD (600–1000 plans).

Keeps y1Plans.csv / y2Actions.csv as the Verify gate (52 plans).
Writes y1Plans_journey.csv + y2Actions_journey.csv (Run=Y, tag Journey).

Usage (from KK/):
  python u/gen_journey_ypad.py              # default ~800 plans
  python u/gen_journey_ypad.py --target 600
  python u/gen_journey_ypad.py --target 1000

Then run via Arena profiles or CLI:
  python FoXYiZ/f/fEngine2.py --config f/fStart/qoa_web.json
  # UI/API slices: Arena Run profiles + Threads, or tags in fStart

Smoke / verify gate:
  python FoXYiZ/f/fEngine2.py --config f/fStart/qoa_web_live.json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from _paths import FOXYIZ_ROOT, KK_ROOT, SUITE_QOA_WEB, SUITE_QOA_WEB_LIVE

SUITE_DIR = SUITE_QOA_WEB
SUITE_SLUG = "qoa_web"
OPEN_SITE_REUSE = "PReuse_qoa_web_OpenSite"

BASE = "http://127.0.0.1:8765"
PERSONA_DATA = KK_ROOT / "Docs" / "test-user-data"

# Shared locators (same for all persona columns in y3Designs)
LOC = {
    "nav_build_btn": "css=button[data-phase='build']",
    "nav_run_btn": "css=button[data-phase='run']",
    "nav_analyze_btn": "css=button[data-phase='analyze']",
    "nav_heal_btn": "css=button[data-phase='heal']",
    "nav_loop_btn": "css=button[data-phase='loop']",
    "nav_brahl_btn": "css=button[data-phase='brahl']",
    "nav_atomic77_btn": "css=button[data-phase='atomic77']",
    "nav_cost_btn": "css=button[data-phase='cost']",
    "nav_promote_btn": "css=button[data-phase='promoter']",
    "avatar_client_bar_btn": "css=.avatar-btn[data-avatar='client']",
    "avatar_hitl_bar_btn": "css=.avatar-btn[data-avatar='consultant']",
    "avatar_networker_bar_btn": "css=.avatar-btn[data-avatar='networker']",
    "profile_chip_code_locator": "css=#profile-chip-code",
    "build_panel_title_locator": "css=#build-panel-title",
    "run_heading_locator": "css=#panel-run h2",
    "analyze_heading_locator": "css=#panel-analyze h2",
    "heal_heading_locator": "css=#panel-heal h2",
    "loop_heading_locator": "css=#panel-loop h2",
    "brahl_heading_locator": "css=#panel-brahl h2",
    "atomic77_heading_locator": "css=#panel-atomic77 h2",
    "promote_heading_locator": "css=#panel-promoter h2",
    "xp_heading_locator": "css=#cost-xp-view h2",
    "cost_project_name_locator": "css=#cost-project-name",
    "chat_input_locator": "css=#chat-input",
    "brahl_chat_input_locator": "css=#brahl-chat-input",
    "atomic77_chat_input_locator": "css=#atomic77-chat-input",
    "budget_block_locator": "css=.budget-block h3",
    "build_refine_summary_locator": "css=#build-refine-details summary",
    "build_checklist_locator": "css=#build-checklist",
    "btn_join_hitl_locator": "css=#btn-join-hitl",
    "btn_shrink_locator": "css=#btn-shrink-plans",
    "btn_restore_locator": "css=#btn-restore-plans",
    "btn_run_locator": "css=#btn-run",
    "btn_refresh_locator": "css=#btn-refresh-runs",
    "btn_analyze_ai_locator": "css=#btn-analyze-ai",
    "btn_heal_ai_locator": "css=#btn-heal-ai",
    "gonogo_section_locator": "css=#gonogo-block h3",
    "hunt_evidence_heading_locator": "css=#hunt-evidence h3",
    "version_launch_heading_locator": "css=#build-change h3",
    "version_baseline_btn_locator": "css=#btn-snapshot-baseline",
    "ypad_explorer_locator": "css=.ypad-tab[data-ypad-tab='plans']",
    "theme_pro_btn": "css=button[data-theme-btn='pro']",
    "theme_arena_btn": "css=button[data-theme-btn='arena']",
    "visual_reward_rail_locator": "css=#visual-reward-rail",
    "promote_post_draft_locator": "css=#promote-post-draft",
    "health_pill_locator": "css=#health-pill",
    "status_bar_locator": "css=#status-bar",
    "phase_progress_locator": "css=#phase-progress",
    "run_scope_locator": "css=#run-project-scope",
    "analyze_scope_locator": "css=#analyze-project-scope",
    "brahl_report_list_locator": "css=#brahl-report-list",
    "btn_link_report_locator": "css=#btn-link-run-report",
    "ai_toggle_label_locator": "css=#ai-toggle-label",
    "consultant_tier_banner_locator": "css=#consultant-tier-banner",
    "btn_new_project_locator": "css=#client-empty-add",
    "add_project_modal_title_locator": "css=#add-project-title",
    "signin_creator_pitch_locator": "css=#signin-creator-pitch",
    "signin_hunter_pitch_locator": "css=#signin-hunter-pitch",
    "waitlist_heading_locator": "css=#waitlist-heading",
    "about_arena_title_locator": "css=#about-arena-title",
    "admin_title_locator": "css=#about-admin-title",
    "atomic77_faq_idea_locator": "css=button.atomic77-faq-chip[data-faq='idea']",
    "demo_banner_locator": "css=#demo-banner",
    "footer_version_locator": "css=#footer-version",
    "topbar_project_label_locator": "css=.topbar-project-label",
    "persona_tasks_strip_locator": "css=#persona-tasks-strip",
    "cost_runtime_local_locator": "css=#cost-runtime-local",
    "cost_meter_fill_locator": "css=#cost-meter-fill",
    "xp_summary_cards_locator": "css=#xp-summary-cards",
    "build_requirement_locator": "css=#build-requirement-text",
    "cycle_history_locator": "css=#cycle-history",
    "btn_hunt_start_locator": "css=#btn-hunt-start",
    "nav_heal_btn_text": "Heal",
    "nav_build_btn_text": "Build",
    "nav_run_btn_text": "Run",
    "nav_analyze_btn_text": "Analyze",
    "nav_loop_btn_text": "Loop",
    "nav_brahl_btn_text": "BRAHL",
    "nav_atomic77_btn_text": "A77",
    "nav_cost_btn_text": "$",
}

EXPECTED = {
    "build_title_client": "Build — qoa_web",
    "build_title_hitl": "Build — qoa_web (QA Hunter)",
    "run_heading": "Run — FoXYiZ fEngine2",
    "analyze_heading": "Analyze — z/",
    "loop_heading": "Loop — BRAHL cycle (FoXYiZ)",
    "brahl_heading": "BRAHL — cycle report",
    "atomic77_heading": "Atomic 77",
    "promote_heading": "Promoter",
    "gonogo_heading": "Launch readiness — Go / No-Go",
    "hunt_heading": "Hunt evidence",
    "version_heading": "App versions & launch compare",
    "baseline_btn": "Save latest Verify as baseline (old version)",
    "join_btn": "Join as QA Hunter",
    "shrink_btn": "Shrink to failures (Loop 2 prep)",
    "budget_h3": "Budget",
    "ypad_plans_tab": "Y Plans",
    "add_challenge": "Add challenge to arena",
    "add_modal_title": "Add challenge",
    "waitlist_h": "Join the waitlist",
    "about_arena": "Champion vs Contender — BRAHL it",
    "admin_h": "What we watch — and why",
    "ai_on": "AI on",
    "ai_off": "AI off (profile)",
    "my_challenge": "My challenge",
    "open_challenges": "Open challenges",
    "health_ok": "ok",
}


@dataclass
class Persona:
    col: str  # D1
    pid: str  # p1
    code: str  # P1
    name: str
    default_avatar: str
    can_client: bool
    can_hunter: bool
    can_networker: bool = True
    profile_url: str = ""

    @property
    def design_id(self) -> str:
        return self.col


def load_personas(suite_slug: str = "qoa_web") -> list[Persona]:
    idx = json.loads((PERSONA_DATA / "index.json").read_text(encoding="utf-8"))
    out: list[Persona] = []
    for entry in idx.get("personas", []):
        p = json.loads((PERSONA_DATA / entry["file"]).read_text(encoding="utf-8"))
        allowed = set(p.get("allowed_avatars") or [])
        pid = p.get("id") or entry.get("id", "")
        col = entry.get("ypad_design_column") or f"D{pid[1:]}" if pid.startswith("p") else "D1"
        out.append(
            Persona(
                col=col,
                pid=pid,
                code=p.get("code") or entry.get("code", ""),
                name=p.get("name") or entry.get("name", ""),
                default_avatar=p.get("default_avatar", "client"),
                can_client="client" in allowed,
                can_hunter="consultant" in allowed,
                profile_url=p.get("profile_url")
                or f"{BASE}/?reset=1&profile={pid}&suite={suite_slug}",
            )
        )
    return out


@dataclass
class Step:
    info: str
    action_type: str
    action_name: str
    input: str = ""
    expected: str = ""
    critical: str = "y"


@dataclass
class Plan:
    plan_id: str
    name: str
    design_id: str
    tags: str
    output: str
    steps: list[Step] = field(default_factory=list)


def slug(s: str, max_len: int = 48) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")
    return s[:max_len]


class JourneyBuilder:
    def __init__(self, target: int = 800, suite_slug: str = "qoa_web") -> None:
        self.target = target
        self.suite_slug = suite_slug
        self.personas = load_personas(suite_slug)
        self.plans: list[Plan] = []
        self._existing_ids: set[str] = set()

    def load_existing_plan_ids(self) -> None:
        verify_plans = SUITE_DIR / "y1Plans.csv"
        if verify_plans.is_file():
            with verify_plans.open(encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    self._existing_ids.add(row["PlanId"])

    def add_plan(self, plan: Plan) -> bool:
        if plan.plan_id in self._existing_ids:
            return False
        if any(p.plan_id == plan.plan_id for p in self.plans):
            return False
        self.plans.append(plan)
        return True

    def shell_steps(self, persona: Persona, avatar: str) -> list[Step]:
        steps = [
            Step("Open site", "xReuse", OPEN_SITE_REUSE),
            Step("Load persona profile", "xUI", "xNavigate", "profile_url"),
            Step("Wait for profile", "xTime", "xTimeWait", "3"),
            Step("Verify profile chip", "xUI", "xGetText", "profile_chip_code_locator", "persona_code"),
        ]
        if avatar == "client" and persona.default_avatar != "client":
            steps.append(Step("Select Creator avatar", "xUI", "xClick", "avatar_client_bar_btn"))
            steps.append(Step("Wait after avatar", "xTime", "xTimeWait", "2"))
        elif avatar == "consultant":
            steps.append(Step("Select QA Hunter avatar", "xUI", "xClick", "avatar_hitl_bar_btn"))
            steps.append(Step("Wait after avatar", "xTime", "xTimeWait", "2"))
        elif avatar == "networker":
            steps.append(Step("Select Networker avatar", "xUI", "xClick", "avatar_networker_bar_btn"))
            steps.append(Step("Wait after avatar", "xTime", "xTimeWait", "2"))
        return steps

    def register_shell_reuse(self, persona: Persona, avatar: str) -> str:
        reuse_id = f"PReuse_J_{persona.code}_Shell_{avatar.title()}"
        if reuse_id in self._existing_ids or any(p.plan_id == reuse_id for p in self.plans):
            return reuse_id
        av_label = {"client": "Creator", "consultant": "Hunter", "networker": "Networker"}[avatar]
        plan = Plan(
            reuse_id,
            f"Journey shell {persona.code} as {av_label}",
            persona.design_id,
            f"Journey;Reuse;{persona.code};{avatar}",
            f"shell_{persona.pid}_{avatar}",
            self.shell_steps(persona, avatar),
        )
        self.add_plan(plan)
        return reuse_id

    def plan_from_shell(
        self,
        persona: Persona,
        avatar: str,
        suffix: str,
        name: str,
        tag_parts: list[str],
        extra_steps: list[Step],
        output: str,
    ) -> None:
        shell = self.register_shell_reuse(persona, avatar)
        steps = [Step("Journey shell ready", "xReuse", shell), *extra_steps]
        plan_id = f"PJ_{persona.code}_{suffix}"
        tags = ";".join(["Journey", self.suite_slug, "Regression", persona.code, *tag_parts])
        self.add_plan(Plan(plan_id, name, persona.design_id, tags, output, steps))

    def generate_phase_nav(self) -> None:
        phase_defs = [
            ("build", "nav_build_btn", "Nav", "Build"),
            ("run", "nav_run_btn", "Nav", "Run"),
            ("analyze", "nav_analyze_btn", "Nav", "Analyze"),
            ("heal", "nav_heal_btn", "Nav", "Heal"),
            ("loop", "nav_loop_btn", "Nav", "Loop"),
            ("brahl", "nav_brahl_btn", "Nav", "BRAHL"),
            ("atomic77", "nav_atomic77_btn", "Nav", "Atomic77"),
            ("cost", "nav_cost_btn", "Nav", "Cost"),
            ("promote", "nav_promote_btn", "Nav", "Promoter"),
        ]
        brahl_avatars = {"client", "consultant"}
        networker_only = {"promote", "atomic77", "cost"}
        for persona in self.personas:
            for avatar in ("client", "consultant", "networker"):
                if avatar == "client" and not persona.can_client:
                    continue
                if avatar == "consultant" and not persona.can_hunter:
                    continue
                for phase_key, nav_loc, cat, label in phase_defs:
                    if avatar == "networker" and phase_key not in networker_only:
                        continue
                    if avatar == "networker" and phase_key in brahl_avatars:
                        continue
                    if avatar != "networker" and phase_key == "promote":
                        continue
                    text_key = f"nav_{phase_key}_btn_text"
                    expected = EXPECTED.get(text_key.replace("_btn_text", "_btn_text"), label)
                    if phase_key == "cost":
                        expected = "$"
                    elif phase_key == "atomic77":
                        expected = "A77"
                    extra = [
                        Step(f"Click {label} tab", "xUI", "xClick", nav_loc),
                        Step("Wait for panel", "xTime", "xTimeWait", "2"),
                        Step(f"Verify {label} nav label", "xUI", "xGetText", nav_loc, expected),
                    ]
                    self.plan_from_shell(
                        persona,
                        avatar,
                        f"{cat}_{phase_key}_{avatar[:3]}",
                        f"{persona.code} {avatar} opens {label} phase",
                        [cat, label, avatar],
                        extra,
                        f"pj_{persona.pid}_{phase_key}_{avatar}_nav",
                    )

    def generate_phase_headings(self) -> None:
        checks = [
            ("build", "nav_build_btn", "build_panel_title_locator", "build_title_client", "build_title_hitl", "Build"),
            ("run", "nav_run_btn", "run_heading_locator", "run_heading", "run_heading", "Run"),
            ("analyze", "nav_analyze_btn", "analyze_heading_locator", "analyze_heading", "analyze_heading", "Analyze"),
            ("heal", "nav_heal_btn", "heal_heading_locator", "shrink_btn", "shrink_btn", "Heal"),
            ("loop", "nav_loop_btn", "loop_heading_locator", "loop_heading", "loop_heading", "Loop"),
            ("brahl", "nav_brahl_btn", "brahl_heading_locator", "brahl_heading", "brahl_heading", "BRAHL"),
            ("atomic77", "nav_atomic77_btn", "atomic77_heading_locator", "atomic77_heading", "atomic77_heading", "Atomic77"),
            ("cost", "nav_cost_btn", "xp_heading_locator", "", "", "Cost"),
            ("promote", "nav_promote_btn", "promote_heading_locator", "promote_heading", "promote_heading", "Promote"),
        ]
        for persona in self.personas:
            for avatar in ("client", "consultant", "networker"):
                if avatar == "consultant" and not persona.can_hunter:
                    continue
                if avatar == "networker":
                    allowed_phases = {"promote", "atomic77", "cost"}
                else:
                    allowed_phases = {"build", "run", "analyze", "heal", "loop", "brahl", "atomic77", "cost"}
                for phase_key, nav, heading_loc, exp_c, exp_h, label in checks:
                    if phase_key not in allowed_phases:
                        continue
                    exp_key = exp_c if avatar == "client" else exp_h
                    expected = EXPECTED.get(exp_key, "") if exp_key else ""
                    if phase_key == "heal":
                        extra = [
                            Step(f"Open {label}", "xUI", "xClick", nav),
                            Step("Wait", "xTime", "xTimeWait", "2"),
                            Step("Verify heal control", "xUI", "xGetText", "btn_shrink_locator", EXPECTED["shrink_btn"]),
                        ]
                    elif phase_key == "cost" and avatar == "consultant":
                        extra = [
                            Step("Open Cost", "xUI", "xClick", nav),
                            Step("Wait", "xTime", "xTimeWait", "2"),
                            Step("Verify wallet view", "xUI", "xGetText", "cost_project_name_locator", ""),
                        ]
                    else:
                        extra = [
                            Step(f"Open {label}", "xUI", "xClick", nav),
                            Step("Wait", "xTime", "xTimeWait", "2"),
                            Step(f"Verify {label} heading", "xUI", "xGetText", heading_loc, expected),
                        ]
                    self.plan_from_shell(
                        persona,
                        avatar,
                        f"Head_{phase_key}_{avatar[:3]}",
                        f"{persona.code} {avatar} {label} panel heading",
                        ["Panel", label, avatar],
                        extra,
                        f"pj_{persona.pid}_{phase_key}_head",
                    )

    def generate_build_workspace(self) -> None:
        build_checks = [
            ("ChatInput", "chat_input_locator", "", "Build chat visible"),
            ("Budget", "budget_block_locator", EXPECTED["budget_h3"], "Budget block"),
            ("Checklist", "build_checklist_locator", "", "Build checklist"),
            ("Requirement", "build_requirement_locator", "", "Requirement quote"),
            ("Refine", "build_refine_summary_locator", "", "Refine section"),
            ("VersionLaunch", "version_launch_heading_locator", EXPECTED["version_heading"], "Version launch"),
            ("BaselineBtn", "version_baseline_btn_locator", EXPECTED["baseline_btn"], "Baseline button"),
            ("YpadTab", "ypad_explorer_locator", EXPECTED["ypad_plans_tab"], "yPAD explorer"),
            ("CycleHistory", "cycle_history_locator", "", "Cycle history"),
            ("AiToggle", "ai_toggle_label_locator", "", "AI toggle label"),
        ]
        for persona in self.personas:
            if not persona.can_client:
                continue
            for slug_name, loc, exp, desc in build_checks:
                extra = [
                    Step("Open Build", "xUI", "xClick", "nav_build_btn"),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                ]
                if slug_name == "Refine":
                    extra.append(Step("Open refine", "xUI", "xClick", loc))
                elif slug_name == "Budget":
                    extra.append(Step("Open refine", "xUI", "xClick", "build_refine_summary_locator"))
                    extra.append(Step("Verify budget", "xUI", "xGetText", loc, exp))
                else:
                    extra.append(Step(f"Verify {desc}", "xUI", "xGetText", loc, exp))
                self.plan_from_shell(
                    persona,
                    "client",
                    f"Build_{slug_name}",
                    f"{persona.code} Creator {desc}",
                    ["Build", slug_name, "Creator"],
                    extra,
                    f"pj_{persona.pid}_build_{slug_name.lower()}",
                )

    def generate_hunter_workspace(self) -> None:
        checks = [
            ("JoinBtn", "btn_join_hitl_locator", EXPECTED["join_btn"]),
            ("HuntEvidence", "hunt_evidence_heading_locator", EXPECTED["hunt_heading"]),
            ("HuntRecord", "btn_hunt_start_locator", "Record hunt"),
            ("ConsultantPanel", "build_consultant_panel_locator", "QA Hunter workspace"),
            ("TierBanner", "consultant_tier_banner_locator", ""),
        ]
        for persona in self.personas:
            if not persona.can_hunter:
                continue
            for slug_name, loc, exp in checks:
                extra = [
                    Step("Open Build", "xUI", "xClick", "nav_build_btn"),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                    Step("Verify hunter UI", "xUI", "xGetText", loc, exp),
                ]
                self.plan_from_shell(
                    persona,
                    "consultant",
                    f"Hunt_{slug_name}",
                    f"{persona.code} Hunter {slug_name}",
                    ["QA_Hunter", slug_name],
                    extra,
                    f"pj_{persona.pid}_hunt_{slug_name.lower()}",
                )

    def generate_brahl_cycle_path(self) -> None:
        """Single-step transitions along BRAHL cycle (FoXYiZ + UI)."""
        cycle = ["build", "run", "analyze", "heal", "loop", "brahl", "cost"]
        nav_map = {
            "build": "nav_build_btn",
            "run": "nav_run_btn",
            "analyze": "nav_analyze_btn",
            "heal": "nav_heal_btn",
            "loop": "nav_loop_btn",
            "brahl": "nav_brahl_btn",
            "cost": "nav_cost_btn",
        }
        for persona in self.personas:
            if not persona.can_client:
                continue
            for i in range(len(cycle) - 1):
                a, b = cycle[i], cycle[i + 1]
                extra = [
                    Step(f"Start at {a}", "xUI", "xClick", nav_map[a]),
                    Step("Wait", "xTime", "xTimeWait", "1"),
                    Step(f"Go to {b}", "xUI", "xClick", nav_map[b]),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                    Step("Verify status bar", "xUI", "xGetText", "status_bar_locator", ""),
                ]
                self.plan_from_shell(
                    persona,
                    "client",
                    f"Cycle_{a}_to_{b}",
                    f"{persona.code} BRAHL cycle {a} → {b}",
                    ["BRAHL", "Cycle", a, b],
                    extra,
                    f"pj_{persona.pid}_cycle_{a}_{b}",
                )

    def generate_avatar_switches(self) -> None:
        switches = [
            ("client", "consultant", "avatar_hitl_bar_btn", "build_title_hitl"),
            ("consultant", "client", "avatar_client_bar_btn", "build_title_client"),
            ("client", "networker", "avatar_networker_bar_btn", "promote_heading"),
            ("networker", "client", "avatar_client_bar_btn", "build_title_client"),
        ]
        for persona in self.personas:
            for src, dst, btn, exp_key in switches:
                if src == "consultant" and not persona.can_hunter:
                    continue
                if dst == "consultant" and not persona.can_hunter:
                    continue
                shell_avatar = src
                extra = [
                    Step(f"Switch to {dst}", "xUI", "xClick", btn),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                ]
                if dst == "networker":
                    extra.append(Step("Open Promote", "xUI", "xClick", "nav_promote_btn"))
                    extra.append(Step("Verify promote", "xUI", "xGetText", "promote_heading_locator", EXPECTED["promote_heading"]))
                elif dst == "consultant":
                    extra.append(Step("Verify hunter title", "xUI", "xGetText", "build_panel_title_locator", EXPECTED[exp_key]))
                else:
                    extra.append(Step("Verify creator title", "xUI", "xGetText", "build_panel_title_locator", EXPECTED[exp_key]))
                self.plan_from_shell(
                    persona,
                    shell_avatar,
                    f"Switch_{src[:3]}_{dst[:3]}",
                    f"{persona.code} switch {src} → {dst}",
                    ["Avatar", "Switch", src, dst],
                    extra,
                    f"pj_{persona.pid}_sw_{src}_{dst}",
                )

    def generate_run_analyze_controls(self) -> None:
        controls = [
            ("Run", "nav_run_btn", "run_scope_locator", "Run scope"),
            ("RunRefresh", "btn_refresh_locator", "", "Refresh runs"),
            ("RunBtn", "btn_run_locator", "", "Run button"),
            ("AnalyzeScope", "nav_analyze_btn", "analyze_scope_locator", "Analyze scope"),
            ("AnalyzeAi", "btn_analyze_ai_locator", "", "Analyze AI"),
            ("HealShrink", "btn_shrink_locator", EXPECTED["shrink_btn"], "Shrink"),
            ("HealRestore", "btn_restore_locator", "", "Restore"),
            ("HealAi", "btn_heal_ai_locator", "", "Heal AI"),
            ("LoopPanel", "loop_heading_locator", EXPECTED["loop_heading"], "Loop heading"),
            ("BrahlList", "brahl_report_list_locator", "", "Report list"),
            ("BrahlChat", "brahl_chat_input_locator", "", "BRAHL chat"),
            ("BrahlGoNoGo", "gonogo_section_locator", EXPECTED["gonogo_heading"], "Go/No-Go"),
            ("LinkReport", "btn_link_report_locator", "", "Link report"),
        ]
        for persona in self.personas:
            if not persona.can_client:
                continue
            for slug_name, nav_or_loc, loc_or_exp, desc in controls:
                extra: list[Step] = []
                if slug_name.startswith("Run") or slug_name == "AnalyzeScope" or slug_name == "AnalyzeAi":
                    phase = "run" if slug_name.startswith("Run") else "analyze"
                    extra.append(Step(f"Open {phase}", "xUI", "xClick", f"nav_{phase}_btn"))
                    extra.append(Step("Wait", "xTime", "xTimeWait", "2"))
                    loc = nav_or_loc if slug_name != "Run" else loc_or_exp
                    if slug_name == "Run":
                        loc = "run_scope_locator"
                    elif slug_name == "RunRefresh":
                        loc = "btn_refresh_locator"
                    elif slug_name == "RunBtn":
                        loc = "btn_run_locator"
                    elif slug_name == "AnalyzeScope":
                        loc = "analyze_scope_locator"
                    elif slug_name == "AnalyzeAi":
                        loc = "btn_analyze_ai_locator"
                    exp = loc_or_exp if isinstance(loc_or_exp, str) and loc_or_exp in EXPECTED else loc_or_exp
                    extra.append(Step(f"Verify {desc}", "xUI", "xGetText", loc, exp if exp else ""))
                elif slug_name.startswith("Heal"):
                    extra.append(Step("Open Heal", "xUI", "xClick", "nav_heal_btn"))
                    extra.append(Step("Wait", "xTime", "xTimeWait", "2"))
                    loc = nav_or_loc
                    exp = loc_or_exp
                    extra.append(Step(f"Verify {desc}", "xUI", "xGetText", loc, exp))
                elif slug_name.startswith("Loop"):
                    extra.append(Step("Open Loop", "xUI", "xClick", "nav_loop_btn"))
                    extra.append(Step("Wait", "xTime", "xTimeWait", "2"))
                    extra.append(Step("Verify loop", "xUI", "xGetText", nav_or_loc, loc_or_exp))
                else:
                    extra.append(Step("Open BRAHL", "xUI", "xClick", "nav_brahl_btn"))
                    extra.append(Step("Wait", "xTime", "xTimeWait", "2"))
                    extra.append(Step(f"Verify {desc}", "xUI", "xGetText", nav_or_loc, loc_or_exp))
                self.plan_from_shell(
                    persona,
                    "client",
                    f"Engine_{slug_name}",
                    f"{persona.code} FoXYiZ {desc}",
                    ["FoXYiZ", slug_name],
                    extra,
                    f"pj_{persona.pid}_eng_{slug_name.lower()}",
                )

    def generate_atomic77_theme(self) -> None:
        faqs = ["idea", "brahl", "launch", "cost", "hunter"]
        for persona in self.personas:
            for avatar in ("client", "consultant", "networker"):
                if avatar == "consultant" and not persona.can_hunter:
                    continue
                extra = [
                    Step("Open A77", "xUI", "xClick", "nav_atomic77_btn"),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                    Step("Verify A77 heading", "xUI", "xGetText", "atomic77_heading_locator", EXPECTED["atomic77_heading"]),
                    Step("Verify chat input", "xUI", "xGetText", "atomic77_chat_input_locator", ""),
                ]
                self.plan_from_shell(
                    persona,
                    avatar,
                    f"A77_Panel_{avatar[:3]}",
                    f"{persona.code} Atomic77 panel as {avatar}",
                    ["Atomic77", avatar],
                    extra,
                    f"pj_{persona.pid}_a77_panel",
                )
                for faq in faqs:
                    extra_faq = [
                        Step("Open A77", "xUI", "xClick", "nav_atomic77_btn"),
                        Step("Wait", "xTime", "xTimeWait", "2"),
                        Step(f"Verify FAQ chip {faq}", "xUI", "xGetText", f"atomic77_faq_{faq}_locator", ""),
                    ]
                    self.plan_from_shell(
                        persona,
                        avatar,
                        f"A77_Faq_{faq}_{avatar[:3]}",
                        f"{persona.code} A77 FAQ {faq}",
                        ["Atomic77", "FAQ", faq],
                        extra_faq,
                        f"pj_{persona.pid}_a77_{faq}",
                    )
            for theme in ("pro", "arena"):
                btn = f"theme_{theme}_btn"
                extra = [
                    Step(f"Click {theme} theme", "xUI", "xClick", btn),
                    Step("Wait", "xTime", "xTimeWait", "1"),
                    Step("Verify theme applied", "xUI", "xGetText", "app_title_locator", ""),
                ]
                av = persona.default_avatar if persona.can_client else "consultant"
                if av == "consultant" and not persona.can_hunter:
                    av = "networker"
                self.plan_from_shell(
                    persona,
                    av if av != "networker" else "client",
                    f"Theme_{theme}",
                    f"{persona.code} theme {theme}",
                    ["Theme", theme],
                    extra,
                    f"pj_{persona.pid}_theme_{theme}",
                )

    def generate_cost_promote(self) -> None:
        cost_checks = [
            ("XpCards", "xp_summary_cards_locator", ""),
            ("CostMeter", "cost_meter_fill_locator", ""),
            ("RuntimeLocal", "cost_runtime_local_locator", ""),
            ("ProjectName", "cost_project_name_locator", ""),
        ]
        for persona in self.personas:
            if persona.can_client:
                for slug_name, loc, exp in cost_checks:
                    extra = [
                        Step("Open Cost", "xUI", "xClick", "nav_cost_btn"),
                        Step("Wait", "xTime", "xTimeWait", "2"),
                        Step("Verify cost UI", "xUI", "xGetText", loc, exp),
                    ]
                    self.plan_from_shell(
                        persona,
                        "client",
                        f"Cost_{slug_name}",
                        f"{persona.code} Cost {slug_name}",
                        ["Cost", "XP", slug_name],
                        extra,
                        f"pj_{persona.pid}_cost_{slug_name.lower()}",
                    )
            extra_promote = [
                Step("Open Promote", "xUI", "xClick", "nav_promote_btn"),
                Step("Wait", "xTime", "xTimeWait", "2"),
                Step("Verify draft area", "xUI", "xGetText", "promote_post_draft_locator", ""),
            ]
            self.plan_from_shell(
                persona,
                "networker",
                "Promote_Draft",
                f"{persona.code} Networker promote draft",
                ["Networker", "Promote"],
                extra_promote,
                f"pj_{persona.pid}_promote",
            )

    def generate_external_pages(self) -> None:
        pages = [
            ("Signin", "signin_url", "waitlist_heading_locator", EXPECTED["waitlist_h"], "Waitlist"),
            ("SigninCreator", "signin_url", "signin_creator_pitch_locator", "", "Signin"),
            ("SigninHunter", "signin_url", "signin_hunter_pitch_locator", "", "Signin"),
            ("About", "about_url", "about_arena_title_locator", EXPECTED["about_arena"], "About"),
            ("Admin", "admin_url", "admin_title_locator", EXPECTED["admin_h"], "Admin"),
        ]
        for persona in self.personas:
            for slug_name, url_key, loc, exp, cat in pages:
                steps = [
                    Step("Open site", "xReuse", OPEN_SITE_REUSE),
                    Step(f"Navigate {cat}", "xUI", "xNavigate", url_key),
                    Step("Wait", "xTime", "xTimeWait", "2"),
                    Step(f"Verify {cat}", "xUI", "xGetText", loc, exp),
                ]
                plan_id = f"PJ_{persona.code}_Ext_{slug_name}"
                tags = f"Journey;{self.suite_slug};Regression;{persona.code};External;{cat}"
                self.add_plan(
                    Plan(
                        plan_id,
                        f"{persona.code} external {cat}",
                        persona.design_id,
                        tags,
                        f"pj_{persona.pid}_ext_{slug_name.lower()}",
                        steps,
                    )
                )

    def generate_api_matrix(self) -> None:
        endpoints = [
            ("Health", "api_health_endpoint", "200"),
            ("Version", "api_version_endpoint", "200"),
            ("Suites", "api_suites_endpoint", "200"),
            ("ProjectsClient", "api_projects_endpoint", "200"),
            ("ProjectsConsultant", "api_projects_consultant_endpoint", "200"),
            ("Runs", "api_runs_endpoint", "200"),
            ("WaitlistCount", "api_waitlist_count_endpoint", "200"),
            ("ProfilesJs", "api_profiles_js_endpoint", "200"),
            ("Index", "api_index_endpoint", "200"),
            ("Styles", "api_css_endpoint", "200"),
            ("AppJs", "api_js_endpoint", "200"),
            ("ThemesCss", "api_themes_css_endpoint", "200"),
            ("ThemeJs", "api_theme_js_endpoint", "200"),
            ("AboutEcosystem", "api_ecosystem_endpoint", "200"),
            ("Signin", "api_signin_endpoint", "200"),
        ]
        for persona in self.personas:
            for name, ep, code in endpoints:
                steps = [
                    Step("Open site", "xReuse", OPEN_SITE_REUSE),
                    Step(f"GET {name}", "xAPI", "xGet", f"api_base_url;{ep}", code),
                ]
                plan_id = f"PJ_{persona.code}_API_{name}"
                tags = f"Journey;{self.suite_slug};Regression;{persona.code};API;{name}"
                self.add_plan(
                    Plan(
                        plan_id,
                        f"{persona.code} API {name}",
                        persona.design_id,
                        tags,
                        f"pj_{persona.pid}_api_{name.lower()}",
                        steps,
                    )
                )

    def generate_shell_ui(self) -> None:
        shell_checks = [
            ("DemoBanner", "demo_banner_locator", ""),
            ("Footer", "footer_version_locator", ""),
            ("HealthPill", "health_pill_locator", EXPECTED["health_ok"]),
            ("PhaseProgress", "phase_progress_locator", ""),
            ("TopbarLabel", "topbar_project_label_locator", ""),
            ("PersonaTasks", "persona_tasks_strip_locator", ""),
            ("StatusBar", "status_bar_locator", ""),
        ]
        for persona in self.personas:
            av = persona.default_avatar
            if av == "client" and not persona.can_client:
                av = "consultant"
            for slug_name, loc, exp in shell_checks:
                extra = [Step("Verify shell", "xUI", "xGetText", loc, exp)]
                self.plan_from_shell(
                    persona,
                    av if av in ("client", "consultant", "networker") else "client",
                    f"Shell_{slug_name}",
                    f"{persona.code} shell {slug_name}",
                    ["Shell", slug_name],
                    extra,
                    f"pj_{persona.pid}_shell_{slug_name.lower()}",
                )

    def generate_p9_nux(self) -> None:
        p9 = next(p for p in self.personas if p.code == "P9")
        extras = [
            ([Step("Verify empty add", "xUI", "xGetText", "btn_new_project_locator", EXPECTED["add_challenge"])], "EmptyAdd"),
            (
                [
                    Step("Click add", "xUI", "xClick", "btn_new_project_locator"),
                    Step("Wait", "xTime", "xTimeWait", "1"),
                    Step("Verify modal", "xUI", "xGetText", "add_project_modal_title_locator", EXPECTED["add_modal_title"]),
                ],
                "AddModal",
            ),
        ]
        for steps, slug_name in extras:
            shell = self.register_shell_reuse(p9, "client")
            self.add_plan(
                Plan(
                    f"PJ_P9_NUX_{slug_name}",
                    f"P9 NUX {slug_name}",
                    p9.design_id,
                    f"Journey;{self.suite_slug};Regression;P9;NUX;{slug_name}",
                    f"pj_p9_nux_{slug_name.lower()}",
                    [Step("P9 shell", "xReuse", shell), *steps],
                )
            )

    def generate_all(self) -> None:
        self.load_existing_plan_ids()
        generators = [
            self.generate_phase_nav,
            self.generate_phase_headings,
            self.generate_build_workspace,
            self.generate_hunter_workspace,
            self.generate_brahl_cycle_path,
            self.generate_avatar_switches,
            self.generate_run_analyze_controls,
            self.generate_atomic77_theme,
            self.generate_cost_promote,
            self.generate_external_pages,
            self.generate_api_matrix,
            self.generate_shell_ui,
            self.generate_p9_nux,
        ]
        for gen in generators:
            gen()
        # Trim or pad toward target (prefer keeping diverse tags)
        if len(self.plans) > self.target:
            self.plans = self.plans[: self.target]
        elif len(self.plans) < self.target:
            # Duplicate-style micro-variations: persona × phase progress dots
            i = 0
            phases = ["build", "run", "analyze", "heal", "loop", "brahl", "cost"]
            while len(self.plans) < self.target:
                persona = self.personas[i % len(self.personas)]
                phase = phases[i % len(phases)]
                extra = [
                    Step("Open phase via progress", "xUI", "xClick", f"nav_{phase}_btn"),
                    Step("Wait", "xTime", "xTimeWait", "1"),
                    Step("Verify progress strip", "xUI", "xGetText", "phase_progress_locator", ""),
                ]
                av = "client" if persona.can_client else "consultant"
                suffix = f"Extra_{i}_{phase}"
                if self.add_plan(
                    Plan(
                        f"PJ_{persona.code}_{suffix}",
                        f"{persona.code} extra navigation {phase} #{i}",
                        persona.design_id,
                        f"Journey;{self.suite_slug};Regression;{persona.code};Extra;{phase}",
                        f"pj_{persona.pid}_extra_{i}",
                        [Step("Shell", "xReuse", self.register_shell_reuse(persona, av)), *extra],
                    )
                ):
                    pass
                i += 1
                if i > self.target * 2:
                    break


def append_design_locators() -> None:
    """Append journey locators to y3Designs.csv if missing."""
    fix_script = Path(__file__).resolve().parent / "fix_y3_journey_locators.py"
    if fix_script.is_file():
        import os
        import runpy

        os.environ["FOXYIZ_SUITE_DIR"] = str(SUITE_DIR)
        runpy.run_path(str(fix_script), run_name="__fix_y3__")
        return


def tag_verify_plans() -> None:
    """Ensure verify gate plans carry Verify tag (for fStart tag filter)."""
    path = SUITE_DIR / "y1Plans.csv"
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            if row.get("Run", "").upper() == "Y":
                tags = row.get("Tags", "")
                if "Verify" not in tags.split(";"):
                    parts = [t.strip() for t in tags.split(";") if t.strip()]
                    parts.insert(0, "Verify")
                    row["Tags"] = ";".join(parts)
            rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_journey_csvs(plans: list[Plan]) -> tuple[int, int]:
    plans_path = SUITE_DIR / "y1Plans_journey.csv"
    actions_path = SUITE_DIR / "y2Actions_journey.csv"
    plan_rows = []
    action_rows = []
    for p in plans:
        plan_rows.append(
            {
                "PlanId": p.plan_id,
                "PlanName": p.name,
                "DesignId": p.design_id,
                "Run": "Y",
                "Tags": p.tags,
                "Output": p.output,
            }
        )
        for i, s in enumerate(p.steps, start=1):
            action_rows.append(
                {
                    "PlanId": p.plan_id,
                    "StepId": str(i),
                    "StepInfo": s.info,
                    "ActionType": s.action_type,
                    "ActionName": s.action_name,
                    "Input": s.input,
                    "Output": "",
                    "Expected": s.expected,
                    "Critical": s.critical,
                }
            )
    with plans_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["PlanId", "PlanName", "DesignId", "Run", "Tags", "Output"])
        w.writeheader()
        w.writerows(plan_rows)
    with actions_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "PlanId",
                "StepId",
                "StepInfo",
                "ActionType",
                "ActionName",
                "Input",
                "Output",
                "Expected",
                "Critical",
            ],
        )
        w.writeheader()
        w.writerows(action_rows)
    return len(plan_rows), len(action_rows)


def update_suite_json(suite_slug: str) -> None:
    cfg_path = SUITE_DIR / f"{suite_slug}.json"
    if not cfg_path.is_file():
        return
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    rel = f"y/{suite_slug}"
    cfg["input_files"]["yPlans"] = [
        f"{rel}/y1Plans.csv",
        f"{rel}/y1Plans_journey.csv",
    ]
    cfg["input_files"]["yActions"] = [
        f"{rel}/y2Actions.csv",
        f"{rel}/y2Actions_journey.csv",
    ]
    cfg["description"] = (
        f"BRAHL web app — verify gate + journey regression library "
        f"({cfg.get('journey_plans', '800+')} plans, tag Journey)"
    )
    cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    global SUITE_DIR, SUITE_SLUG, OPEN_SITE_REUSE
    ap = argparse.ArgumentParser(description="Generate BRAHL journey yPAD library")
    ap.add_argument("--target", type=int, default=None, help="Target plan count")
    ap.add_argument(
        "--suite",
        choices=("qoa_web", "qoa_web_live"),
        default="qoa_web",
        help="yPAD suite folder under y/",
    )
    args = ap.parse_args()

    SUITE_SLUG = args.suite
    SUITE_DIR = SUITE_QOA_WEB_LIVE if SUITE_SLUG == "qoa_web_live" else SUITE_QOA_WEB
    OPEN_SITE_REUSE = "PReuse_qoa_web_OpenSite"

    if args.target is None:
        target = 300 if SUITE_SLUG == "qoa_web_live" else 800
    else:
        target = args.target
    if SUITE_SLUG == "qoa_web_live":
        target = max(150, min(500, target))
    else:
        target = max(600, min(1000, target))

    append_design_locators()
    tag_verify_plans()

    builder = JourneyBuilder(target=target, suite_slug=SUITE_SLUG)
    builder.generate_all()
    n_plans, n_steps = write_journey_csvs(builder.plans)

    cfg_path = SUITE_DIR / f"{SUITE_SLUG}.json"
    if cfg_path.is_file():
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        cfg["journey_plans"] = n_plans
        if SUITE_SLUG == "qoa_web_live":
            cfg["version"] = cfg.get("version", "1.4.0-v1")
            cfg["description"] = (
                "BRAHL Arena live gate (V1 verify) + Journey library (re-BRAHL'd). Current /app UX."
            )
        else:
            cfg["version"] = cfg.get("version", "1.2.0")
        cfg_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    update_suite_json(SUITE_SLUG)

    verify_path = SUITE_DIR / "y1Plans.csv"
    verify_count = 0
    if verify_path.is_file():
        verify_count = sum(
            1
            for row in csv.DictReader(verify_path.open(encoding="utf-8"))
            if row.get("Run", "").upper() == "Y"
        )
    print(f"Suite: {SUITE_SLUG} @ {SUITE_DIR}")
    print(f"Journey library: {n_plans} plans, {n_steps} action steps (target {target})")
    print(f"Verify gate unchanged: {verify_count} plans in y1Plans.csv (tag Verify)")
    if SUITE_SLUG == "qoa_web_live":
        print("Run: python FoXYiZ\\f\\fEngine2.py --config f/fStart/qoa_web_live_journey_nav.json")
    else:
        print("Run: python FoXYiZ\\f\\fEngine2.py --config f/fStart/qoa_web_regression.json")


if __name__ == "__main__":
    main()
