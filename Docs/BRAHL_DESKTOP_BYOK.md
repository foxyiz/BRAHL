# BRAHL desktop — BYOK AI (bring your own key)

**Who pays for LLM:** the person running the desktop app. FoXYiZ Run/Loop never call OpenAI; only Build / Analyze / Heal / Planner / BRAHL chat / Atomic 77 do.

## Token-smart prompts

In-app AI packs only:

- `Docs/AI_GUARDRAILS.md`
- `Docs/BRAHL_PROMPT.md`

Full FoXYiZ/BRAHL references stay in the AI docs viewer (`in_prompt: false`). See also Cursor skill `.cursor/skills/brahl-desktop-ui/`.

## Setup

1. Copy or edit `FoXYiZ/f/.env`:
   ```
   OPENAI_API_KEY=sk-...
   OPENAI_MODEL=gpt-4o-mini
   ```
2. Leave `QOA_AI_HOSTED` unset (default = **BYOK / desktop**). Quotas are soft; your API bill is yours.
3. Start: `python qoa_web/run_local.py` → http://127.0.0.1:8765

Check `GET /api/ai/status` — `"byok": true`, `"available": true` when the key loads.

## Hosted / multi-tenant (when you subsidize AI)

```
QOA_AI_HOSTED=1
QOA_AI_USER_MONTHLY_TOKENS=500000
QOA_AI_PROJECT_TOKENS=200000
QOA_AI_USD_PER_1K=0.0004
OPENAI_API_KEY=sk-platform-...
```

Hard stops apply: monthly user tokens, project tokens, and automation wallet pool. Usage is stored in `qoa_web/data/ai_usage.json` and mirrored on `project.ai_usage`.

## GitHub desktop packaging notes

- Ship `FoXYiZ/` (`f`/`x`/`y`) + `qoa_web/` + lean samples (e.g. Math).
- Document BYOK in README — never commit real keys.
- Base44/SaaS is optional later for managed hosting; still use quotas if the platform key is shared.

## Cost control product rules

| Mode | Limit behavior |
|------|----------------|
| Desktop BYOK | Key required; no hard platform deny (user monitors their OpenAI bill) |
| Hosted | Deny AI when user month, project tokens, or automation wallet exhausted |

Project Wallet ($) surfaces `ai_usage.total_tokens` / `usd_est` via cost meter.
