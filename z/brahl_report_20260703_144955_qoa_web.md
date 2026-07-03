# BRAHL Report — qoa_web — 2026-07-03 (full feature suite v0.3)

**App:** http://127.0.0.1:8765/
**Scope:** 42 plans · Build, Run, Analyze, Heal, Loop, BRAHL, HITL, API
**Config:** f/fStart_qoa_web_verify.json
**Verify:** z/20260703_144955_qoa_web/ — **42/42 pass** (~47s)

---

## Executive summary

All six BRAHL phases plus avatar gate, AI toggle, project scope, HITL consultant view, and REST APIs are covered by yPAD. Loop 1 failures were healed (exact Expected matching, fresh_url for avatar gate reset). **Verify is 42/42 green.**

---

## Cycle summary

| Step | Plans | Pass | Fail | z/ folder |
|------|-------|------|------|-----------|
| Loop 1 | 42 | 24 | 18 | z/20260703_144303_qoa_web |
| Heal | y2Actions Expected, fresh_url, HITL Build tab | — | — | — |
| Loop 2 | 42 | 39 | 3 | z/20260703_144645_qoa_web |
| Loop 3 | 42 | 42 | 0 | z/20260703_144955_qoa_web |

---

## Features verified

- **Build:** AI chat, context +, budget, project select, new project, manual mode hint
- **Run:** fStart config, Run engine, project scope line
- **Analyze:** Refresh runs, runs list, project scope
- **Heal:** T1/T2/T3 checklist, project scope
- **Loop:** Step 0 prompt, Capture, Loop 1, Verify full
- **BRAHL:** Report list, model chat input, link verify run
- **Avatar:** Client gate (fresh_url reset), HITL switch + consultant Build
- **API:** health, configs, suites, projects, brahl reports/chat, jobs, context, static assets

---

## Verdict

- [x] Automation complete for in-scope set
- [x] Verify run green
- [x] Full Run=Y restored for CI / user regression

**Dashboard:** z/20260703_144955_qoa_web/qoa_web_zDash.html
