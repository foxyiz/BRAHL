"""Optional OpenAI assist for BRAHL Build, Analyze, and Heal (when AI toggle is on).

Run and Loop stay on FoXYiZ fEngine2.py — no LLM in the execution path.
See KK/Docs/BRAHL.md and KK/Docs/FoXYiZ.md.

AI cost control
---------------
- Desktop / BYOK: user supplies OPENAI_API_KEY in f/.env — platform pays $0.
- Hosted: platform key + hard quotas (monthly tokens + project wallet automation pool).
All LLM calls go through `_chat` / `chat_metered` so usage is recorded and denied when over quota.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from paths import KK_ROOT, F_DIR, resolve_repo
DOCS_DIR = KK_ROOT / "Docs"
USAGE_PATH = KK_ROOT / "qoa_web" / "data" / "ai_usage.json"

_DOC_CACHE: dict[str, str] = {}
_usage_lock = threading.Lock()


def invalidate_doc_cache() -> None:
    """Clear packed prompt doc cache after user/builtin context changes."""
    _DOC_CACHE.clear()

# Role → (doc_chars, history_turns, max_completion_tokens)
AI_ROLE_BUDGETS: dict[str, tuple[int, int, int]] = {
    # (doc_chars, history_turns, max_completion_tokens)
    "planner": (2800, 4, 600),
    "build": (4200, 6, 800),
    "brahl_chat": (4200, 6, 800),
    "analyze": (4500, 0, 1000),
    "heal": (4500, 0, 1000),
    "atomic77": (2600, 4, 500),
    "default": (4200, 4, 800),
}

GUARDRAIL_PREAMBLE = (
    "GUARDRAILS: Spell BRAHL/FoXYiZ correctly. ≤120 words unless asked for a table. "
    "Never invent locators. Never run FoXYiZ yourself — send user to Run/Loop. "
    "Prefer one next action. No LLM on Run/Loop."
)

# Defaults — override via env for hosted trials
DEFAULT_USER_MONTHLY_TOKEN_CAP = int(os.environ.get("QOA_AI_USER_MONTHLY_TOKENS", "500000"))
DEFAULT_PROJECT_TOKEN_SOFT_CAP = int(os.environ.get("QOA_AI_PROJECT_TOKENS", "200000"))
# Rough USD per 1K tokens (prompt+completion blended) for gpt-4o-mini ballpark
USD_PER_1K_TOKENS = float(os.environ.get("QOA_AI_USD_PER_1K", "0.0004"))


def _load_dotenv() -> None:
    env_path = F_DIR / ".env"
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


def is_byok_mode() -> bool:
    """True when AI key is local BYOK (desktop). Hosted sets QOA_AI_HOSTED=1."""
    return os.environ.get("QOA_AI_HOSTED", "").strip() not in ("1", "true", "True", "yes")


def _month_key(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m")


def _empty_bucket() -> dict[str, Any]:
    return {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "usd_est": 0.0,
    }


def _load_usage_store() -> dict[str, Any]:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not USAGE_PATH.is_file():
        return {"users": {}, "projects": {}, "global": _empty_bucket()}
    try:
        return json.loads(USAGE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"users": {}, "projects": {}, "global": _empty_bucket()}


def _save_usage_store(data: dict[str, Any]) -> None:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    USAGE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _estimate_tokens(text: str) -> int:
    # ~4 chars/token heuristic when API usage is missing
    return max(1, len(text or "") // 4)


def get_usage_snapshot(
    user_id: str | None = None,
    project_id: str | None = None,
) -> dict[str, Any]:
    month = _month_key()
    with _usage_lock:
        store = _load_usage_store()
        user_rec = (store.get("users") or {}).get(user_id or "", {})
        proj_rec = (store.get("projects") or {}).get(project_id or "", {})
        user_month = dict(user_rec.get("months", {}).get(month) or _empty_bucket())
        proj_all = dict(proj_rec.get("all") or _empty_bucket())
        glob = dict(store.get("global") or _empty_bucket())

    user_cap = DEFAULT_USER_MONTHLY_TOKEN_CAP
    membership_tier = None
    if user_id:
        try:
            import auth as auth_store
            from pricing import hunter_ai_token_cap

            user = auth_store.get_user(user_id)
            if user and user.get("membership_active"):
                membership_tier = float(user.get("hunter_ai_tier_usd") or 0)
                tier_cap = hunter_ai_token_cap(membership_tier)
                if tier_cap:
                    user_cap = max(user_cap, int(tier_cap))
        except Exception:
            pass
    proj_cap = DEFAULT_PROJECT_TOKEN_SOFT_CAP
    user_left = max(0, user_cap - int(user_month.get("total_tokens") or 0))
    proj_left = max(0, proj_cap - int(proj_all.get("total_tokens") or 0))
    return {
        "byok": is_byok_mode(),
        "hosted": not is_byok_mode(),
        "month": month,
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini") if is_ai_available() else None,
        "available": is_ai_available(),
        "membership_tier_usd": membership_tier,
        "user": {
            "id": user_id,
            "month": user_month,
            "cap_tokens": user_cap,
            "remaining_tokens": user_left,
        },
        "project": {
            "id": project_id,
            "all": proj_all,
            "cap_tokens": proj_cap,
            "remaining_tokens": proj_left,
        },
        "global": glob,
        "usd_per_1k": USD_PER_1K_TOKENS,
    }


def check_ai_quota(
    user_id: str | None = None,
    project_id: str | None = None,
    project: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return {ok, reason}. BYOK desktop: only require key. Hosted: enforce caps + wallet."""
    if not is_ai_available():
        return {
            "ok": False,
            "reason": "No OPENAI_API_KEY — add your key to f/.env (BYOK) or ask an admin.",
            "code": "no_key",
        }
    if project is not None and project.get("ai_enabled") is False:
        return {"ok": False, "reason": "AI is off for this project.", "code": "ai_off"}

    snap = get_usage_snapshot(user_id, project_id)

    # Soft wallet check — automation pool depleted blocks hosted AI
    if project and not is_byok_mode():
        budget = float(project.get("budget_usd") or 0)
        if budget > 0:
            split = project.get("budget_split") or {}
            auto_pct = float(split.get("automation_pct", 50)) / 100.0
            auto_pool = budget * auto_pct
            spent = float((project.get("ai_usage") or {}).get("usd_est") or 0)
            if spent >= auto_pool > 0:
                return {
                    "ok": False,
                    "reason": f"Project AI wallet exhausted (~${spent:.2f} / ${auto_pool:.2f} automation pool). Top up or turn AI off.",
                    "code": "wallet",
                }

    if not is_byok_mode():
        if user_id and snap["user"]["remaining_tokens"] <= 0:
            return {
                "ok": False,
                "reason": f"Monthly AI token cap reached ({snap['user']['cap_tokens']:,}). Resets next month or raise QOA_AI_USER_MONTHLY_TOKENS.",
                "code": "user_cap",
            }
        if project_id and snap["project"]["remaining_tokens"] <= 0:
            return {
                "ok": False,
                "reason": f"Project AI token cap reached ({snap['project']['cap_tokens']:,}).",
                "code": "project_cap",
            }
    return {"ok": True, "reason": "", "code": "ok", "snapshot": snap}


def record_ai_usage(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    user_id: str | None = None,
    project_id: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    prompt_tokens = max(0, int(prompt_tokens))
    completion_tokens = max(0, int(completion_tokens))
    total = prompt_tokens + completion_tokens
    usd = round(total / 1000.0 * USD_PER_1K_TOKENS, 6)
    month = _month_key()
    entry = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total,
        "usd_est": usd,
        "model": model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "at": datetime.now(timezone.utc).isoformat(),
    }

    def _add(bucket: dict[str, Any]) -> None:
        bucket["calls"] = int(bucket.get("calls") or 0) + 1
        bucket["prompt_tokens"] = int(bucket.get("prompt_tokens") or 0) + prompt_tokens
        bucket["completion_tokens"] = int(bucket.get("completion_tokens") or 0) + completion_tokens
        bucket["total_tokens"] = int(bucket.get("total_tokens") or 0) + total
        bucket["usd_est"] = round(float(bucket.get("usd_est") or 0) + usd, 6)

    with _usage_lock:
        store = _load_usage_store()
        store.setdefault("global", _empty_bucket())
        _add(store["global"])
        if user_id:
            users = store.setdefault("users", {})
            urec = users.setdefault(user_id, {"months": {}})
            months = urec.setdefault("months", {})
            m = months.setdefault(month, _empty_bucket())
            _add(m)
        if project_id:
            projects = store.setdefault("projects", {})
            prec = projects.setdefault(project_id, {"all": _empty_bucket(), "months": {}})
            _add(prec.setdefault("all", _empty_bucket()))
            _add(prec.setdefault("months", {}).setdefault(month, _empty_bucket()))
        _save_usage_store(store)
    return entry


def brahl_doc_context(
    max_chars: int = 3500,
    role: str = "default",
    project: dict[str, Any] | None = None,
) -> str:
    """Pack Journey (this project) + Master (everyone) + opted-in My docs within role budget."""
    budget = AI_ROLE_BUDGETS.get(role, AI_ROLE_BUDGETS["default"])[0]
    max_chars = min(max_chars, budget)
    pid = (project or {}).get("id") or ""
    cache_key = f"{role}:{max_chars}:{pid}:{bool(project)}"
    if not project and cache_key in _DOC_CACHE:
        return _DOC_CACHE[cache_key]

    chunks: list[str] = []
    remaining = max_chars
    try:
        import ai_docs

        for spec in ai_docs.prompt_doc_specs(project=project):
            if remaining <= 80:
                break
            cap = min(int(spec.get("prompt_chars") or remaining), remaining)
            inline = spec.get("content")
            if inline:
                text = str(inline)[:cap]
                # Journey markdown already includes its own H1
                if spec.get("source") == "journey" or text.lstrip().startswith("#"):
                    block = text
                else:
                    title = spec.get("title") or spec.get("id") or "doc.md"
                    block = f"# {title}\n{text}"
            else:
                path = resolve_repo(spec["path"]) if spec.get("path") else None
                if not path or not path.is_file():
                    continue
                raw = path.read_text(encoding="utf-8")
                block = f"# {path.name}\n{raw[:cap]}"
            chunks.append(block)
            remaining -= len(block) + 8
    except Exception:
        for name in ("AI_GUARDRAILS.md", "BRAHL_PROMPT.md"):
            if remaining <= 80:
                break
            path = DOCS_DIR / name
            if path.is_file():
                block = f"# {name}\n{path.read_text(encoding='utf-8')[:remaining]}"
                chunks.append(block)
                remaining -= len(block) + 8
        if project:
            try:
                import ai_docs

                j = f"# journey.md\n{ai_docs.build_project_journey_md(project)[:1600]}"
                chunks.insert(0, j[: max_chars])
            except Exception:
                pass

    text = "\n\n---\n\n".join(chunks) if chunks else (
        "BRAHL: Build yPAD → Run FoXYiZ → Analyze z/ → Heal y/ → Loop. Spell BRAHL/FoXYiZ."
    )
    packed = text[:max_chars]
    if not project:
        _DOC_CACHE[cache_key] = packed
    return packed


def _trim_history(
    history: list[dict[str, str]] | None,
    max_turns: int,
    max_chars_each: int = 400,
) -> list[dict[str, str]]:
    if not history or max_turns <= 0:
        return []
    out: list[dict[str, str]] = []
    for msg in history[-max_turns:]:
        role = msg.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        text = (msg.get("text") or "")[:max_chars_each]
        out.append({"role": role, "text": text})
    return out


def chat_metered(
    system: str,
    user: str,
    history: list[dict[str, str]] | None = None,
    *,
    user_id: str | None = None,
    project_id: str | None = None,
    project: dict[str, Any] | None = None,
    on_usage: Callable[[dict[str, Any]], None] | None = None,
    role: str = "default",
    max_tokens: int | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """LLM call with quota check + usage record. Returns (reply, meta)."""
    gate = check_ai_quota(user_id=user_id, project_id=project_id, project=project)
    if not gate.get("ok"):
        return None, {"ok": False, "denied": True, "reason": gate.get("reason"), "code": gate.get("code")}

    _doc_chars, hist_turns, default_max = AI_ROLE_BUDGETS.get(role, AI_ROLE_BUDGETS["default"])
    if max_tokens is None:
        max_tokens = default_max
    trimmed = _trim_history(history, hist_turns)
    # Cap user blob — oversized paste burns tokens
    user = (user or "")[:3500]
    system = f"{GUARDRAIL_PREAMBLE}\n\n{system}"[:6000]

    try:
        from openai import OpenAI

        client = OpenAI()
        messages: list[dict[str, str]] = [{"role": "system", "content": system}]
        for msg in trimmed:
            messages.append({"role": msg["role"], "content": msg["text"]})
        messages.append({"role": "user", "content": user})
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=max_tokens,
        )
        content = resp.choices[0].message.content
        reply = content.strip() if content else None
        usage = getattr(resp, "usage", None)
        if usage:
            pt = int(getattr(usage, "prompt_tokens", 0) or 0)
            ct = int(getattr(usage, "completion_tokens", 0) or 0)
        else:
            joined = system + "\n" + user + "\n" + (reply or "")
            pt = _estimate_tokens(joined) * 2 // 3
            ct = _estimate_tokens(reply or "")
        entry = record_ai_usage(
            prompt_tokens=pt,
            completion_tokens=ct,
            user_id=user_id,
            project_id=project_id,
            model=model,
        )
        if on_usage:
            try:
                on_usage(entry)
            except Exception:
                pass
        return reply, {"ok": True, "denied": False, "usage": entry, "role": role}
    except Exception as exc:
        return None, {"ok": False, "denied": False, "error": str(exc)}


def _chat(system: str, user: str, history: list[dict[str, str]] | None = None) -> str | None:
    """Backward-compatible unscoped chat (still metered under anonymous / global)."""
    reply, _meta = chat_metered(system, user, history, user_id=None, project_id=None)
    return reply


def build_assistant_reply(
    project: dict[str, Any],
    user_text: str,
    on_usage: Callable[[dict[str, Any]], None] | None = None,
) -> str | None:
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
        + brahl_doc_context(role="build", project=project)
    )
    user = (
        f"Project: {project.get('name')} (y/{suite}/)\n"
        f"App URL: {project.get('app_url') or 'not set'}\n"
        f"Purpose so far: {purpose or '(none)'}\n"
        f"Budget: ${float(project.get('budget_usd') or 0):.0f}\n"
        f"Context items:\n{ctx_lines or '(none)'}\n\n"
        f"User message: {user_text}"
    )
    reply, meta = chat_metered(
        system,
        user,
        history,
        project_id=project.get("id"),
        project=project,
        user_id=project.get("owner_user_id"),
        on_usage=on_usage,
        role="build",
    )
    if meta.get("denied"):
        return meta.get("reason") or "AI quota exceeded."
    return reply


def analyze_run_rca(
    project: dict[str, Any],
    run_name: str,
    failures: list[dict[str, str]],
    errors_csv: str = "",
) -> str | None:
    """AI root-cause analysis — classify T1/T2/T3/A1 per BRAHL Analyze."""
    if not failures and not (errors_csv or "").strip():
        return None
    gate = check_ai_quota(
        user_id=project.get("owner_user_id"),
        project_id=project.get("id"),
        project=project,
    )
    if not gate.get("ok"):
        return f"## AI quota\n\n{gate.get('reason')}"

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
        "## Summary\n"
        "## Classification table\n"
        "Use a real GFM table:\n"
        "| PlanId | Step | Class | Root cause | Recommended action |\n"
        "| --- | --- | --- | --- | --- |\n"
        "For Recommended action give a concrete before→after example "
        "(e.g. Expected `12` → `13`, or locator `css=#old` → `css=#new`).\n"
        "## Next steps (Heal vs app bug)\n\n"
        + brahl_doc_context(role="analyze", project=project)
    )
    user = (
        f"Suite: y/{suite}/\nRun: z/{run_name}/\n"
        f"Project purpose: {(project.get('purpose') or '')[:400]}\n\n"
        f"Failures from zResults:\n{fail_text or '(none)'}\n\n"
        f"_errors.csv excerpt:\n{errors_csv[:2500] or '(empty)'}"
    )
    reply, meta = chat_metered(
        system,
        user,
        project_id=project.get("id"),
        project=project,
        user_id=project.get("owner_user_id"),
        role="analyze",
    )
    if meta.get("denied"):
        return f"## AI quota\n\n{meta.get('reason')}"
    return reply


def heal_suggestions(
    project: dict[str, Any],
    run_name: str,
    failures: list[dict[str, str]],
    rca_markdown: str = "",
    suite_config: str = "",
) -> str | None:
    """AI heal suggestions — yPAD edits only for T1/T2/T3; document A1.

    Returns markdown that MUST end with a ```json patches block when CSV edits are safe.
    """
    if not failures:
        return None
    suite = project.get("suite_name") or "unknown"
    fail_text = "\n".join(
        f"- {f.get('planId')} step {f.get('stepId')}: {f.get('output', '')[:150]}"
        for f in failures[:20]
    )
    system = (
        "You are a FoXYiZ/BRAHL Heal assistant. Suggest minimal yPAD fixes for T1/T2/T3 only.\n"
        "Priority: yD_Common/yD_Secure locators → y2Actions steps → y1Plans Tags → y3Designs.\n"
        "Never weaken A1 tests. Prefer xNavigate to reset session; no xWaitFor.\n"
        "NEVER set Run (Y/N) in patches — Shrink/Restore owns Run flags.\n"
        "Output markdown with ## Heal plan (GFM table of PlanId | Step | Field | Before | After) "
        "and ## Verify after heal.\n"
        "ALWAYS end with a fenced JSON block the Arena can Apply:\n"
        "```json\n"
        '{"patches":[{"sheet":"y2Actions","match":{"PlanId":"P1","StepId":"2"},'
        '"set":{"Expected":"..."},"class":"T1","note":"why"}]}\n'
        "```\n"
        "sheet must be one of: y1Plans, y2Actions, y3Designs (or plans/actions/designs).\n"
        "Only set safe CSV fields: Input, Expected, StepInfo, Tags, D1–D9.\n"
        "Omit A1 defects from patches (empty array if nothing safe).\n"
        "Never invent PlanId/StepId — only use ids from the failure list.\n\n"
        + brahl_doc_context(role="heal", project=project)
    )
    user = (
        f"Suite: {suite_config or f'y/{suite}/'}\nRun: {run_name}\n\n"
        f"Prior RCA:\n{rca_markdown[:3000] or '(run Analyze AI first)'}\n\n"
        f"Failures:\n{fail_text}"
    )
    reply, meta = chat_metered(
        system,
        user,
        project_id=project.get("id"),
        project=project,
        user_id=project.get("owner_user_id"),
        role="heal",
        max_tokens=1200,
    )
    if meta.get("denied"):
        return f"## AI quota\n\n{meta.get('reason')}"
    return reply


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
            "AI is off or no API key — add **OPENAI_API_KEY** to `f/.env` (BYOK desktop) or toggle **AI on**. "
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
        + brahl_doc_context(role="atomic77", project=project)
    )
    user = (
        f"Avatar: {avatar_label}\n"
        f"Project: {name}\n"
        f"Purpose: {purpose[:500] or '(not set)'}\n\n"
        f"User: {user_text}"
    )
    reply, meta = chat_metered(
        system,
        user,
        history,
        project_id=(project or {}).get("id"),
        project=project,
        user_id=(project or {}).get("owner_user_id"),
        role="atomic77",
    )
    if meta.get("denied"):
        return meta.get("reason") or "AI quota exceeded.", 20
    if not reply:
        return (
            "I couldn't reach the AI service — check OPENAI_API_KEY or try an FAQ chip.",
            30,
        )
    usage = meta.get("usage") or {}
    tokens_est = int(usage.get("total_tokens") or max(50, (len(user_text) + len(reply)) // 4))
    return reply, tokens_est
