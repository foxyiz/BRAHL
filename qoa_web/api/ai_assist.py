"""Optional OpenAI assist for BRAHL Build, Analyze, and Heal (when AI toggle is on).

Run and Loop stay on FoXYiZ fEngine2.py — no LLM in the execution path.
See KK/Docs/BRAHL.md and KK/Docs/FoXYiZ.md.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

KK_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = KK_ROOT / "Docs"

_DOC_CACHE: str | None = None


def _load_dotenv() -> None:
    env_path = KK_ROOT / "f" / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()


def is_ai_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def brahl_doc_context(max_chars: int = 14000) -> str:
    global _DOC_CACHE
    if _DOC_CACHE is not None:
        return _DOC_CACHE
    chunks: list[str] = []
    try:
        import ai_docs

        for rel in ai_docs.prompt_doc_paths():
            path = KK_ROOT / rel.replace("/", "\\")
            if path.is_file():
                chunks.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    except Exception:
        for name in ("BRAHL_PROMPT.md", "FoXYiZ.md"):
            path = DOCS_DIR / name
            if path.is_file():
                chunks.append(f"# {name}\n{path.read_text(encoding='utf-8')}")
    text = "\n\n---\n\n".join(chunks) if chunks else "BRAHL: Build yPAD → Run FoXYiZ → Analyze z/ → Heal y/ → Loop."
    _DOC_CACHE = text[:max_chars]
    return _DOC_CACHE


def _chat(system: str, user: str, history: list[dict[str, str]] | None = None) -> str | None:
    if not is_ai_available():
        return None
    try:
        from openai import OpenAI

        client = OpenAI()
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for msg in history or []:
            role = msg.get("role", "user")
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg.get("text", "")})
        messages.append({"role": "user", "content": user})
        resp = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.3,
            max_tokens=1800,
        )
        content = resp.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def build_assistant_reply(project: dict[str, Any], user_text: str) -> str | None:
    """AI Build assistant — purpose, connectors, budget, yPAD scope."""
    suite = project.get("suite_name") or "project"
    purpose = project.get("purpose") or project.get("prompt") or ""
    ctx_items = project.get("context_items") or []
    ctx_lines = "\n".join(f"- {c.get('label', c.get('kind'))}: {c.get('value', '')}" for c in ctx_items[:12])
    history = [
        {"role": m.get("role"), "text": m.get("text", "")}
        for m in (project.get("chat_messages") or [])[-8:]
        if m.get("role") in ("user", "assistant")
    ]
    system = (
        "You are the BRAHL Build assistant for FoXYiZ automation.\n"
        "Build phase: define WHAT to test in yPAD (y1Plans, y2Actions, y3Designs) — no app code changes.\n"
        "Guide the user: purpose → connectors/context → budget split (automation vs QA Hunter).\n"
        "When user sends [Change request], acknowledge the rebuild scope and list concrete next steps "
        "(yPAD tabs, QA Hunter stories, connectors, Run/Loop/Verify, BRAHL tab for reports).\n"
        "Run and Loop use fEngine2.py only (no AI during execution). Analyze and Heal can use AI when opted in.\n"
        "Be concise, actionable, reference y/ folder and tags when relevant.\n\n"
        + brahl_doc_context(8000)
    )
    user = (
        f"Project: {project.get('name')} (y/{suite}/)\n"
        f"App URL: {project.get('app_url') or 'not set'}\n"
        f"Purpose so far: {purpose or '(none)'}\n"
        f"Budget: ${float(project.get('budget_usd') or 0):.0f}\n"
        f"Context items:\n{ctx_lines or '(none)'}\n\n"
        f"User message: {user_text}"
    )
    return _chat(system, user, history)


def analyze_run_rca(
    project: dict[str, Any],
    run_name: str,
    failures: list[dict[str, str]],
    errors_csv: str = "",
) -> str | None:
    """AI root-cause analysis — classify T1/T2/T3/A1 per BRAHL Analyze."""
    if not failures and not errors_csv.strip():
        return None
    suite = project.get("suite_name") or "unknown"
    fail_text = "\n".join(
        f"- {f.get('planId')} step {f.get('stepId')} | {f.get('actionName', '')} | "
        f"input={f.get('input', '')[:80]} | output={f.get('output', '')[:120]} | "
        f"expected={f.get('expected', '')[:80]}"
        for f in failures[:30]
    )
    system = (
        "You are a FoXYiZ/BRAHL Analyze assistant. Perform root-cause analysis on z/ failures.\n"
        "Classify each failure: T1 (yPAD/locator/step), T2 (engine), T3 (environment), A1 (application defect).\n"
        "Use the BRAHL RCA decision tree. Do not suggest weakening A1 tests.\n"
        "Output markdown with:\n"
        "## Summary\n## Classification table (PlanId | Step | Class | Root cause | Recommended action)\n"
        "## Next steps (Heal vs app bug)\n\n"
        + brahl_doc_context(6000)
    )
    user = (
        f"Suite: y/{suite}/\nRun: z/{run_name}/\n"
        f"Project purpose: {(project.get('purpose') or '')[:400]}\n\n"
        f"Failures from zResults:\n{fail_text or '(none)'}\n\n"
        f"_errors.csv excerpt:\n{errors_csv[:2500] or '(empty)'}"
    )
    return _chat(system, user)


def heal_suggestions(
    project: dict[str, Any],
    run_name: str,
    failures: list[dict[str, str]],
    rca_markdown: str = "",
    suite_config: str = "",
) -> str | None:
    """AI heal suggestions — yPAD edits only for T1/T2/T3; document A1."""
    if not failures:
        return None
    suite = project.get("suite_name") or "unknown"
    fail_text = "\n".join(
        f"- {f.get('planId')} step {f.get('stepId')}: {f.get('output', '')[:150]}"
        for f in failures[:20]
    )
    system = (
        "You are a FoXYiZ/BRAHL Heal assistant. Suggest minimal yPAD fixes for T1/T2/T3 only.\n"
        "Priority: yD_Common/yD_Secure locators → y2Actions steps → y1Plans Run/Tags → y3Designs.\n"
        "Never weaken A1 tests. Prefer xNavigate to reset session; no xWaitFor.\n"
        "Output markdown: ## Heal plan | per-failure file + exact CSV change | ## Verify after heal\n\n"
        + brahl_doc_context(6000)
    )
    user = (
        f"Suite: {suite_config or f'y/{suite}/'}\nRun: {run_name}\n\n"
        f"Prior RCA:\n{rca_markdown[:3000] or '(run Analyze AI first)'}\n\n"
        f"Failures:\n{fail_text}"
    )
    return _chat(system, user)


ATOMIC77_FAQ: dict[str, str] = {
    "idea": (
        "Start with your idea in one paragraph. Use **Build** for project scope, then ask me how to turn it into "
        "yPAD plans and a BRAHL verify gate. Creators often budget $500+ with a QA Hunter slice."
    ),
    "brahl": (
        "BRAHL = Build → Run → Analyze → Heal → Loop → report. FoXYiZ runs yPAD from Run/Loop; "
        "Atomic 77 helps you scope what belongs in y/ before you BRAHL it."
    ),
    "launch": (
        "Launch path: Verify green → save version baseline → ship new build → Go/No-Go on the BRAHL tab. "
        "QA Hunters add hunt evidence automation misses."
    ),
    "cost": (
        "Open the **$** tab: ~$5/mo membership · Creators fund QA wallets from **$50+** · QAonAIR retains **5%** · "
        "split across AI, human payouts, and ops. Earn via QA Hunting or Promoting. Payout at **$100+** or spend on your own QA."
    ),
    "hunter": (
        "QA Hunters (and any avatar): join challenges, hunt, promote — wallet credits on the **$** tab. "
        "Cash out at **$100+** or apply balance to QA-hunt your own apps."
    ),
}


def atomic77_faq_reply(faq_key: str) -> str | None:
    return ATOMIC77_FAQ.get(faq_key)


def atomic77_assistant_reply(
    project: dict[str, Any] | None,
    user_text: str,
    avatar: str = "client",
    faq_key: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> tuple[str, int]:
    """Returns (reply_text, tokens_est). FAQ keys work without OpenAI."""
    if faq_key and faq_key in ATOMIC77_FAQ:
        text = ATOMIC77_FAQ[faq_key]
        return text, max(40, len(text) // 4)

    if faq_key:
        key = faq_key.lower().strip()
        for k, v in ATOMIC77_FAQ.items():
            if k in key or key in k:
                return v, max(40, len(v) // 4)

    if not is_ai_available():
        return (
            "AI is off or no API key — toggle **AI on** in the top bar, or tap an FAQ chip above. "
            "You can still use Build, Run, and BRAHL phases manually.",
            50,
        )

    name = (project or {}).get("name") or "your challenge"
    purpose = (project or {}).get("purpose") or (project or {}).get("prompt") or ""
    avatar_label = {"client": "Creator", "consultant": "QA Hunter", "networker": "Networker"}.get(
        avatar, "Creator"
    )
    system = (
        "You are **Atomic 77**, the idea-to-launch assistant inside QA on Air / BRAHL Web.\n"
        "Many paying users are Creators building apps — help them scope ideas, FAQs, budgets, yPAD, "
        "and the path to Go/No-Go launch. QA Hunters: hunting and evidence. Networkers: sharing and XP.\n"
        "Never pretend to run FoXYiZ — direct them to Run/Loop tabs. Be concise, warm, actionable.\n"
        "Reference: idea → Build → BRAHL → launch. Community rewards effort via $ and XP.\n\n"
        + brahl_doc_context(6000)
    )
    user = (
        f"Avatar: {avatar_label}\n"
        f"Project: {name}\n"
        f"Purpose: {purpose[:500] or '(not set)'}\n\n"
        f"User: {user_text}"
    )
    reply = _chat(system, user, history)
    if not reply:
        return (
            "I couldn't reach the AI service — check OPENAI_API_KEY or try an FAQ chip.",
            30,
        )
    tokens_est = max(50, (len(user_text) + len(reply)) // 4)
    return reply, tokens_est
