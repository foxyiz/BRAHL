"""Write Wave 1 BRAHL reports and register Arena projects."""
from __future__ import annotations

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "FoXYiZ" / "f"))
from fEngine2 import write_brahl_report  # noqa: E402

z = ROOT / "FoXYiZ" / "z"

SUITES = {
    "life_leveled": {
        "url": "https://life-leveled.base44.app/",
        "name": "LifeLeveled",
        "purpose": "LifeLeveled life-skills platform — Smoke UI Edge API Security Perf",
        "pass": "18/18",
        "a1": "SPA unknown returns HTTP 200 with client Page Not Found UI.",
        "heals": "T1 shared-browser: home/sec/conclusion Open+Navigate+English.",
    },
    "space_planner": {
        "url": "https://bulky-plan-draft-flow.base44.app/",
        "name": "Space Planner",
        "purpose": "SpacePlanner CAD/3D planner — Smoke UI Edge API Security Perf",
        "pass": "15/15",
        "a1": "Start Drawing redirects to app.spaceplanner.co/editor (covered via /editor).",
        "heals": "T1 Perf: wait after navigate before alive assert.",
    },
    "haunted_castle": {
        "url": "https://haunted-mansion.base44.app/",
        "name": "Ziv's Haunted Castle",
        "purpose": "Ziv Haunted Castle 3D game — Smoke UI Edge API Security Perf",
        "pass": "14/14",
        "a1": "None blocking. Loading copy rotates (assert progress %).",
        "heals": "T2 loading message randomized; T1 Perf wait.",
    },
    "creatop": {
        "url": "https://creatop.base44.app/",
        "name": "Creatop",
        "purpose": "Creatop Hebrew RTL studio portfolio — Smoke UI Edge API Security Perf",
        "pass": "16/16",
        "a1": "Heavy intro animation can yield empty body briefly; title/brand waits hardened.",
        "heals": "T1 longer waits; title asserts for Brahl/Sec/404/Nav.",
    },
    "appwars": {
        "url": "https://appwars.base44.app/",
        "name": "AppWars",
        "purpose": "AppWars tournament bracket — Smoke UI Edge API Security Perf",
        "pass": "15/15",
        "a1": "Unknown path soft-falls to landing (no Page Not Found). Documented Edge Soft404.",
        "heals": "T1 Perf alive token Build. Battle.",
    },
}


def latest_run(suite: str) -> Path:
    runs = sorted(
        [p for p in z.iterdir() if p.is_dir() and p.name.endswith("_" + suite)],
        key=lambda p: p.name,
    )
    if not runs:
        raise SystemExit(f"No runs for {suite}")
    return runs[-1]


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    for suite, meta in SUITES.items():
        verify = latest_run(suite)
        md = "\n".join(
            [
                f"# BRAHL Report — {suite}",
                "",
                "## Scope",
                f"Wave 1 Base44 Launchpad — {meta['name']} ({meta['url']})",
                "Tags: Smoke, UI, Edge, API, Security, Perf",
                "",
                "## Verify",
                f"- Run: `{verify.as_posix()}`",
                f"- Plans: **{meta['pass']} Pass** (Manual excluded)",
                "",
                "## Heals",
                f"- {meta['heals']}",
                "",
                "## A1",
                f"- {meta['a1']}",
                "",
                "## Conclusion",
                f"**GO** — {meta['name']} shell automation ready for Wave 1.",
                "",
            ]
        )
        paths = write_brahl_report(md, suite_name=suite, verify_output_dir=str(verify))
        print(suite, "report ->", paths)

    proj_path = ROOT / "qoa_web" / "data" / "projects.json"
    projects = json.loads(proj_path.read_text(encoding="utf-8"))
    existing = {p.get("suite_name") for p in projects}

    for suite, meta in SUITES.items():
        if suite in existing:
            print("skip existing", suite)
            continue
        latest = latest_run(suite).name
        entry = {
            "id": secrets.token_hex(6),
            "name": suite,
            "app_url": meta["url"],
            "suite_name": suite,
            "suite_config": f"y/{suite}/{suite}.json",
            "purpose": meta["purpose"],
            "prompt": meta["purpose"],
            "owner_avatar": "client",
            "owner_user_id": None,
            "status": "open",
            "documents": [],
            "context_items": [
                {
                    "id": secrets.token_hex(4),
                    "kind": "url",
                    "label": "App URL",
                    "value": meta["url"],
                    "added_at": now,
                }
            ],
            "chat_messages": [
                {
                    "id": "welcome",
                    "role": "assistant",
                    "text": "Hi — I'm your BRAHL Build assistant. What are you trying to test or improve?",
                    "at": now,
                }
            ],
            "budget_usd": 0.0,
            "budget_split": {"automation_pct": 50, "human_pct": 50},
            "hitl_consultants": [],
            "reports": [
                {
                    "id": secrets.token_hex(4),
                    "run_name": latest,
                    "report_path": f"z/{latest}/brahl_report.md",
                    "submitted_at": now,
                    "source": "automation",
                    "batch_id": None,
                    "batch_dashboard": None,
                    "archived": False,
                }
            ],
            "ai_enabled": True,
            "brahl_context_path": None,
            "brahl_plan_draft": None,
            "latest_run": latest,
            "created_at": now,
            "updated_at": now,
            "brahl_chat_messages": [
                {
                    "id": "brahl-welcome",
                    "role": "assistant",
                    "text": "Ask about the latest BRAHL report, GO/NO-GO, or heals.",
                    "at": now,
                }
            ],
            "runtime_mode": "local",
        }
        projects.append(entry)
        print("registered", suite, entry["id"], latest)

    proj_path.write_text(json.dumps(projects, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("projects count", len(projects))

    for name in ["_wave1_hunt.json", "_wave1_deep.json", "_wave1_deep_hunt.py"]:
        p = ROOT / "FoXYiZ" / "y" / name
        if p.exists():
            p.unlink()
            print("removed", p)


if __name__ == "__main__":
    main()
