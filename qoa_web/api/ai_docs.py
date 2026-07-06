"""Shared AI context documents — global across all projects (not per-project)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]

# Canonical .md files shown in AI docs viewer (skills, rules, BRAHL, FoXYiZ, README).
AI_CONTEXT_DOCS: list[dict[str, Any]] = [
    {
        "id": "brahl",
        "title": "BRAHL",
        "subtitle": "Build · Run · Analyze · Heal · Loop lifecycle",
        "path": "Docs/BRAHL.md",
        "kind": "skill",
        "in_prompt": False,
    },
    {
        "id": "brahl-prompt",
        "title": "BRAHL (prompt)",
        "subtitle": "Slim lifecycle context for in-app AI",
        "path": "Docs/BRAHL_PROMPT.md",
        "kind": "skill",
        "in_prompt": True,
    },
    {
        "id": "foxyiz",
        "title": "FoXYiZ",
        "subtitle": "f(x,y)=z automation skill · yPAD contract",
        "path": "Docs/FoXYiZ.md",
        "kind": "skill",
        "in_prompt": True,
    },
    {
        "id": "rules",
        "title": "Agent rules",
        "subtitle": "Team conventions · Playwright · Heal scope",
        "path": "Docs/rules.md",
        "kind": "rules",
        "in_prompt": False,
    },
    {
        "id": "foxyiz-readme",
        "title": "FoXYiZ README",
        "subtitle": "LCNC framework overview for end users",
        "path": "Docs/README.md",
        "kind": "readme",
        "in_prompt": False,
    },
    {
        "id": "brahl-web-readme",
        "title": "BRAHL Web README",
        "subtitle": "qoa_web local app · API · verify",
        "path": "qoa_web/README.md",
        "kind": "readme",
        "in_prompt": False,
    },
    {
        "id": "qoa-user-doc",
        "title": "BRAHL Web user guide",
        "subtitle": "End users & AI — personas, phases, Creator vs QA Hunter",
        "path": "qoa_web/qoa_userDoc.md",
        "kind": "readme",
        "in_prompt": True,
    },
    {
        "id": "test-user-data",
        "title": "Test user data",
        "subtitle": "Fictional personas P1–P9 · Creator & QA Hunter tasks",
        "path": "Docs/test-user-data/README.md",
        "kind": "reference",
        "in_prompt": False,
    },
    {
        "id": "atomic77",
        "title": "Atomic 77",
        "subtitle": "Idea → launch plugin · FAQ · builder assistant",
        "path": "Docs/ATOMIC77.md",
        "kind": "skill",
        "in_prompt": True,
    },
    {
        "id": "summary",
        "title": "Team Summary",
        "subtitle": "Suites, commands, handoff index",
        "path": "Summary.md",
        "kind": "readme",
        "in_prompt": False,
    },
]


def _resolve(rel: str) -> Path:
    return KK_ROOT / rel.replace("/", "\\")


def list_ai_docs() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for spec in AI_CONTEXT_DOCS:
        path = _resolve(spec["path"])
        exists = path.is_file()
        size = path.stat().st_size if exists else 0
        out.append(
            {
                "id": spec["id"],
                "title": spec["title"],
                "subtitle": spec.get("subtitle", ""),
                "path": spec["path"],
                "kind": spec.get("kind", "doc"),
                "in_prompt": bool(spec.get("in_prompt")),
                "exists": exists,
                "size_bytes": size,
            }
        )
    return out


def get_ai_doc(doc_id: str) -> dict[str, Any] | None:
    spec = next((d for d in AI_CONTEXT_DOCS if d["id"] == doc_id), None)
    if not spec:
        return None
    path = _resolve(spec["path"])
    if not path.is_file():
        return {
            **spec,
            "content": f"# Missing\n\nFile not found: `{spec['path']}`",
            "exists": False,
        }
    content = path.read_text(encoding="utf-8")
    return {
        "id": spec["id"],
        "title": spec["title"],
        "subtitle": spec.get("subtitle", ""),
        "path": spec["path"],
        "kind": spec.get("kind", "doc"),
        "in_prompt": bool(spec.get("in_prompt")),
        "exists": True,
        "content": content,
    }


def prompt_doc_paths() -> list[str]:
    return [d["path"] for d in AI_CONTEXT_DOCS if d.get("in_prompt")]
