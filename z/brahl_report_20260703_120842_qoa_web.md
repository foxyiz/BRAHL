# BRAHL Report — qoa_web — 2026-07-03 (full feature suite)

**App:** http://127.0.0.1:8765/
**Scope:** Full suite (26 plans) · **Config:** /fStart_qoa_web.json
**Engine:** fEngine2.py · timeout=6 · headless=false
**Context:** z/brahl_context_20260703_120803_qoa_web.json
**Verify:** z/20260703_120842_qoa_web/ — **26/26 pass** (~16s)

---

## Executive summary

Expanded qoa_web from **5 smoke plans → 26 full-feature plans** covering all BRAHL UI tabs, Run/Analyze/Loop controls, and REST API endpoints. After one T1 heal (Loop Verify button label), **Verify is 26/26 green**.

---

## Origin — user prompt

> Add detailed plans to test all features in this web app that we build locally for qoa_web. Loop it and provide final report through brahl.

**Reference documents:** qoa_web/PRD.md

---

### yPAD baseline (before Loop 1)

- **yPlans files:** `y/qoa_web/y1Plans.csv`
- **Total rows:** 27 · **Run=Y:** 26 · **Run=N:** 1 · **Reuse blocks:** 1

**Run=Y plans:**

- `PWeb_OpenHome`
- `PWeb_VerifyTitle`
- `PWeb_StatusBar`
- `PWeb_Tagline`
- `PWeb_Nav_FivePhases`
- `PWeb_Panel_Build`
- `PWeb_Panel_Run`
- `PWeb_Panel_Analyze`
- `PWeb_Panel_Heal`
- `PWeb_Panel_Loop`
- `PWeb_Build_Checklist`
- `PWeb_Build_SuiteCards`
- `PWeb_Run_Controls`
- `PWeb_Analyze_Controls`
- `PWeb_Loop_Step0`
- `PWeb_Footer_Health`
- `PAPI_Health`
- `PAPI_Configs`
- `PAPI_Suites`
- `PAPI_RunsList`
- `PAPI_RunNotFound`
- `PAPI_JobCreate`
- `PAPI_Context`
- `PAPI_StaticCss`
- `PAPI_StaticJs`
- `PAPI_HomePage`

**Run=N plans:**

- `PReuse_qoa_web_OpenSite`


### yPAD after BRAHL (Verify state)

- **yPlans files:** `y/qoa_web/y1Plans.csv`
- **Total rows:** 27 · **Run=Y:** 26 · **Run=N:** 1 · **Reuse blocks:** 1

**Run=Y plans:**

- `PWeb_OpenHome`
- `PWeb_VerifyTitle`
- `PWeb_StatusBar`
- `PWeb_Tagline`
- `PWeb_Nav_FivePhases`
- `PWeb_Panel_Build`
- `PWeb_Panel_Run`
- `PWeb_Panel_Analyze`
- `PWeb_Panel_Heal`
- `PWeb_Panel_Loop`
- `PWeb_Build_Checklist`
- `PWeb_Build_SuiteCards`
- `PWeb_Run_Controls`
- `PWeb_Analyze_Controls`
- `PWeb_Loop_Step0`
- `PWeb_Footer_Health`
- `PAPI_Health`
- `PAPI_Configs`
- `PAPI_Suites`
- `PAPI_RunsList`
- `PAPI_RunNotFound`
- `PAPI_JobCreate`
- `PAPI_Context`
- `PAPI_StaticCss`
- `PAPI_StaticJs`
- `PAPI_HomePage`

**Run=N plans:**

- `PReuse_qoa_web_OpenSite`


---

## yPAD delta

| Before | After | Change |
|--------|-------|--------|
| 5 Run=Y (smoke) | **26 Run=Y** | +21 feature plans |

---

## Feature coverage matrix

### UI — BRAHL phases (Build · Run · Analyze · Heal · Loop)

| PlanId | Feature tested |
|--------|----------------|
| PWeb_OpenHome | Landing page loads |
| PWeb_VerifyTitle | #app-title present |
| PWeb_StatusBar | Status bar |
| PWeb_Tagline | Hero tagline |
| PWeb_Nav_FivePhases | All 5 nav buttons (Build/Run/Analyze/Heal/Loop) |
| PWeb_Panel_Build | Build tab + panel heading |
| PWeb_Panel_Run | Run tab + panel |
| PWeb_Panel_Analyze | Analyze tab + panel |
| PWeb_Panel_Heal | Heal tab + panel |
| PWeb_Panel_Loop | Loop tab + panel |
| PWeb_Build_Checklist | Build checklist items |
| PWeb_Build_SuiteCards | Suite cards from /api/suites |
| PWeb_Run_Controls | fStart label + Run engine button |
| PWeb_Analyze_Controls | Refresh runs + runs list |
| PWeb_Loop_Step0 | Prompt field, Capture context, Verify — full |
| PWeb_Footer_Health | Footer health pill |

### API — FoXYiZ bridge

| PlanId | Endpoint | Expected |
|--------|----------|----------|
| PAPI_Health | GET /api/health | 200 |
| PAPI_Configs | GET /api/configs | 200 |
| PAPI_Suites | GET /api/suites | 200 |
| PAPI_RunsList | GET /api/runs?suite=qoa_web | 200 |
| PAPI_RunNotFound | GET /api/runs/fake_run_xyz/failures | 404 |
| PAPI_JobCreate | POST /api/jobs | 200 |
| PAPI_Context | POST /api/context | 200 |
| PAPI_StaticCss | GET /assets/styles.css | 200 |
| PAPI_StaticJs | GET /assets/app.js | 200 |
| PAPI_HomePage | GET / | 200 |

---

## Cycle summary

| Step | Plans | Pass | Fail | Time | z/ folder |
|------|-------|------|------|------|-----------|
| Loop 1 | 26 | 25 | 1 | ~18s | z/20260703_120805_qoa_web/ |
| Loop 2 | — | — | — | skipped | *1 failure healed* |
| Loop 3 | — | — | — | skipped | — |
| Verify | 26 | **26** | **0** | ~16s | z/20260703_120842_qoa_web/ |

---

## Loop detail

### Loop 1 — failure
- **PWeb_Loop_Step0 step 6** — Expected Verify but button text is Verify — full (T1 yPAD)

### Heal (T1)
- y/qoa_web/y2Actions.csv — step 6 Expected → Verify — full

### Verify
- **26/26 pass**, no regressions

---

## Classification tally

| Class | Count | Notes |
|-------|-------|-------|
| T1 yPAD | 1 | Button label exact match |
| T2 Engine | 0 | — |
| T3 Environment | 0 | Server on :8765 required |
| A1 Application | 0 | — |

---

## yPAD changes

- y/qoa_web/y1Plans.csv — 5 → 26 runnable plans
- y/qoa_web/y2Actions.csv — full UI + API steps
- y/qoa_web/y3Designs.csv — locators for all panels and API paths
- y/qoa_web/payload_job.json, payload_context.json — API POST bodies

---

## Verdict

- [x] All qoa_web UI phases covered by automation
- [x] All REST API endpoints covered
- [x] Verify **26/26** green
- [x] BRAHL report saved under z/

**Dashboard:** z/20260703_120842_qoa_web/qoa_web_zDash.html
**BRAHL report:** z/20260703_120842_qoa_web/brahl_report.md
