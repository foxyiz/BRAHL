# AI guardrails — desktop BRAHL (token-smart)

Sticky rules for qoa_web in-app AI and for agents working in KK.

## Mission

Be a **thin control plane** for FoXYiZ. Maximize signal per token. Prefer scripted FAQ / offline templates when the key is missing or the question is FAQ-shaped.

## Always

- Spell **BRAHL** and **FoXYiZ** correctly ([terminology.md](./terminology.md)).
- Scope answers to the **active project** (name, URL, purpose, latest run).
- Use **BRAHL_PROMPT** lifecycle — do not invent new phases.
- Truncate; use bullets; one primary next step.

## Never

- Put LLM into Run/Loop execution.
- Dump entire yPAD CSVs or `z/` HTML into prompts.
- Weaken assertions to force green (A1 = app defect).
- Spend tokens explaining Playwright as the primary path — FoXYiZ is the engine.

## Context budget (implemented in `ai_assist`)

| Role | Doc budget | History | Completion max_tokens |
|------|------------|---------|------------------------|
| Planner | ~2.5k chars | last 4 | 600 |
| Build / BRAHL chat | ~3.5k | last 6 | 800 |
| Analyze / Heal | ~4k | 0–2 | 1000 |
| Atomic 77 | ~2k | last 4 | 500 |

Hosted mode (`QOA_AI_HOSTED=1`): enforce wallet + monthly token caps before each call.

## Memory for humans

- Project purpose / Step 0 origin lives on the project + `brahl_context_*`.
- Usage: `qoa_web/data/ai_usage.json` + Wallet cost meter.
- Lean session start for builders: `qoa_web/MEMORY.md` only.
