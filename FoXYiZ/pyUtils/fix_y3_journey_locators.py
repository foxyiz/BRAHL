"""Fix y3Designs.csv rows where DataName was dropped on append."""
from __future__ import annotations

import csv
from pathlib import Path

import os
from _paths import SUITE_QOA_WEB

def _suite_dir() -> Path:
    env = os.environ.get("FOXYIZ_SUITE_DIR")
    return Path(env) if env else SUITE_QOA_WEB

ADDITIONS = {
    "nav_atomic77_btn": "css=button[data-phase='atomic77']",
    "atomic77_heading_locator": "css=#panel-atomic77 h2",
    "atomic77_chat_input_locator": "css=#atomic77-chat-input",
    "atomic77_faq_idea_locator": "css=button.atomic77-faq-chip[data-faq='idea']",
    "atomic77_faq_brahl_locator": "css=button.atomic77-faq-chip[data-faq='brahl']",
    "atomic77_faq_launch_locator": "css=button.atomic77-faq-chip[data-faq='launch']",
    "atomic77_faq_cost_locator": "css=button.atomic77-faq-chip[data-faq='cost']",
    "atomic77_faq_hunter_locator": "css=button.atomic77-faq-chip[data-faq='hunter']",
    "theme_pro_btn": "css=button[data-theme-btn='pro']",
    "theme_arena_btn": "css=button[data-theme-btn='arena']",
    "visual_reward_rail_locator": "css=#visual-reward-rail",
    "btn_restore_locator": "css=#btn-restore-plans",
    "btn_analyze_ai_locator": "css=#btn-analyze-ai",
    "btn_heal_ai_locator": "css=#btn-heal-ai",
    "promote_post_draft_locator": "css=#promote-post-draft",
    "cost_runtime_local_locator": "css=#cost-runtime-local",
    "cost_meter_fill_locator": "css=#cost-meter-fill",
    "xp_summary_cards_locator": "css=#xp-summary-cards",
    "cost_project_name_locator": "css=#cost-project-name",
    "cycle_history_locator": "css=#cycle-history",
    "btn_hunt_start_locator": "css=#btn-hunt-start",
    "demo_banner_locator": "css=#demo-banner",
    "status_bar_locator": "css=#status-bar",
    "persona_tasks_strip_locator": "css=#persona-tasks-strip",
    "build_requirement_locator": "css=#build-requirement-text",
    "api_themes_css_endpoint": "/assets/themes.css",
    "api_theme_js_endpoint": "/assets/theme.js",
    "api_ecosystem_endpoint": "/api/about/ecosystem",
    "atomic77_heading": "Atomic 77",
}


def is_corrupt_row(parts: list[str]) -> bool:
    if len(parts) < 2 or parts[0] != "UI":
        return False
    dn = parts[1]
    return dn.startswith(("css=", "http", "/")) or dn == "Atomic 77"


def main() -> None:
    path = _suite_dir() / "y3Designs.csv"
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        cols = [c for c in fieldnames if c.startswith("D")]
        rows = [r for r in reader if not is_corrupt_row([r.get("Type", ""), r.get("DataName", "")])]
    existing = {r["DataName"] for r in rows if r.get("DataName")}
    for name, val in ADDITIONS.items():
        if name in existing:
            continue
        row = {"Type": "UI", "DataName": name, **{c: val for c in cols}}
        rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"Fixed y3Designs.csv — {len(rows)} rows, {len(ADDITIONS)} journey locators ensured")


if __name__ == "__main__":
    main()
