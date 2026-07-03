# BRAHL Report — qoa_web — 2026-07-03

**App:** http://127.0.0.1:8765/  
**Scope:** Smoke · **Config:** `f/fStart_qoa_web_smoke.json`  
**Context:** `z/brahl_context_20260703_115521_qoa_web.json`  
**Verify:** `z/20260703_115545_qoa_web/` — **5/5 pass** (~4s)

## Origin

> Build qoa_web BRAHL local web app and validate with FoXYiZ smoke on localhost:8765

**Reference documents:** `qoa_web/PRD.md`

## Cycle summary

| Step | Plans | Pass | Fail | Time | z/ folder |
|------|-------|------|------|------|-----------|
| Loop 1 | 5 | 4 | 1 | ~5s | `z/20260703_115523_qoa_web/` |
| Loop 2 (re-run) | 5 | **5** | **0** | ~4s | `z/20260703_115545_qoa_web/` |

## Heal (T1)

- `PWeb_Build_Panel` step 4 — panel h2 is `Build — yPAD`, not exact `Build`; cleared `Expected` (presence check)

## Verdict

- [x] qoa_web serves BRAHL UI + API on localhost:8765
- [x] Smoke 5/5 green after heal
- [x] API `/api/health` validated

**Dashboard:** `z/20260703_115545_qoa_web/qoa_web_zDash.html`
