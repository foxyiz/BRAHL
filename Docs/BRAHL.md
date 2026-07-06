# BRAHL — KK / qoa_web quick reference

> **Full skill reference** continues below (FoXYiZ lifecycle, qoa2 lessons, heal tables).
> **Slim in-app version:** [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) · **Session hygiene:** [MAINTENANCE.md](./MAINTENANCE.md)

**Active workspace:** KK/ · **App:** qoa_web @ http://127.0.0.1:8765 · **Suite:** y/qoa_web/

| Item | Value |
|------|-------|
| Verify config | /fStart_qoa_web_verify.json |
| Plans (Run=Y) | **45** (4 reuse plans stay Run=N) |
| Tag filter | ll → all Run=Y plans |
| Personas | P1–P9 in Docs/test-user-data/ → python u/sync_personas.py |
| Utilities | u/cleaner.py, u/yVisualizer.py, u/zDefects.py — HTML reports in u/ |
| Avatars | Creator · QA Hunter · Networker (all profiles can switch) |

## Loop protocol (required)

`
Loop 1   full Run=Y → analyze → heal
Loop 2   Run=N on passes → failures only → heal
Loop 3   remaining failures → heal
Verify   restore all Run=Y → full run → BRAHL report
`

**Go/No-Go** and **version compare** live on the BRAHL tab (Creator). Do not weaken assertions for A1 app defects.

---

---
name: brahl
description: >-
  BRAHL lifecycle for QAonAir and FoXYiZ automation: Build yPAD CSVs, Run with
  foxyiz, Analyze z/ results, Heal y-plans/actions/designs, Loop until only app
  defects remain. Use when authoring tests, triaging failures, root-cause analysis,
  healing yPAD, or explaining Build/Run/Analyze/Heal/Loop to humans or agents.
  Trigger on BRAHL, heal, loop, root cause, qoa2, QAonAir, yPAD fix, zResults.
---

# BRAHL — Build · Run · Analyze · Heal · Loop

Skill document for **human testers** and **AI agents** working with [FoXYiZ](https://foxyiz.com) and [QAonAir2 (qoa2)](https://qoa2.base44.app/).

**Formula:** `f(x, y) = z` — engine + yPAD → results.

**BRAHL** names the full quality lifecycle twice:

| Layer | What BRAHL means |
|-------|------------------|
| **QAonAir product** | How teams plan, execute, review, fix, and repeat testing inside the app (Build → Run → Analyze → Heal → Loop pages in qoa2). |
| **FoXYiZ automation** | How we author yPAD, execute tests, read `z/`, fix automation, and re-run until failures are **application defects**, not test defects. |

This document focuses on the **FoXYiZ automation loop**, aligned with the product model on qoa2.

---

## The five phases (FoXYiZ view)

```
  ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌─────────┐    ┌─────────┐
  │  BUILD  │───▶│   RUN   │───▶│ ANALYZE  │───▶│  HEAL   │───▶│  LOOP   │
  │  y/     │    │  f/     │    │  z/      │    │  y/     │    │ repeat  │
  └─────────┘    └─────────┘    └──────────┘    └─────────┘    └─────────┘
       ▲                                                              │
       └──────────────────── until only app defects remain ───────────┘
```

---

## B — Build

**Goal:** Define *what* to test and *how* in yPAD files. No application code changes.

### Artifacts

| File | Role |
|------|------|
| `y/<suite>/y1Plans.csv` | Plans: `PlanId`, `DesignId`, `Run`, `Tags`, `Output` |
| `y/<suite>/y2Actions.csv` | Steps: `ActionType`, `ActionName`, `Input`, `Expected`, `Critical` |
| `y/<suite>/y3Designs.csv` + `Common/yD_*.csv` | Data & locators per design column D1, D2, … |
| `y/<suite>/<suite>.json` | Suite config (`input_files` merge list) |

### Build practices

1. **Explore first** — Browse the app (manual, Playwright MCP, or DevTools). Record stable locators and post-login landing URLs.
2. **Reuse blocks** — `PReuse_<Suite>_OpenSite`, `_Login`, `_Dashboard`, `_Admin` with `Run=N`; invoke via `xReuse`.
3. **Tag every runnable plan** — Semicolon-separated tags (`qoa2;Admin;Smoke`) for `fStart.json` filtering.
4. **Personas via DesignId** — e.g. D1 = regular user, D2 = admin (`yD_Secure.csv`).
5. **One concern per plan** — Prefer focused plans; consolidate only to avoid duplicate login/session cost.
6. **Do not** maintain Python CSV generators for operators — edit yPAD directly.
7. **A1 defect plans** — When exploration finds broken routes, dead links, missing elements, or security gaps, add **Issue** / **Link** / **Security** / **Element** plans that **pass when the defect is present** (document A1 in the BRAHL report; do not weaken assertions to force green).

### A1 defect plan tags

| Tag | Use when | Example plan |
|-----|----------|--------------|
| `Issue` | Route or feature returns 404 / wrong page | `PWeb_Issue_Shop_404` → expect "Page Not Found" |
| `Link` | Nav or CTA must reach a live page (fails if broken) | `PWeb_Link_Dashboard_Gifts` → click "Send Gift", expect Gift Shop |
| `Security` | Auth gate missing, XSS surface, public sensitive page | `PWeb_Sec_Dashboard_Public`, `PWeb_Sec_XSS_Login` |
| `Element` | Required UI block missing or empty state wrong | `PWeb_Elem_Dashboard_EmptyOrders` |

Add new plans during **Build** or after **Analyze** when z/ reveals app-only failures. List every A1 in the report **A1 defects** table with PlanId, evidence path, and repro URL.

### Build exit criteria

- [ ] Suite JSON loads all CSV paths
- [ ] Every `ActionName` exists in `x/xCapa.csv` for its `ActionType`
- [ ] Reuse plans marked `Run=N`
- [ ] Smoke-tagged plans cover login + one critical path
- [ ] Known app issues documented in `PlanName` or `Tags` (`Issue`, `Regression`)

### QAonAir product mapping (qoa2)

| BRAHL phase | In-app area (qoa2) |
|-------------|-------------------|
| **Build** | BRAHL **Build** — plans, cases, strategy |
| Product UI | `/build`, landing BRAHL section, onboarding “BRAHL Cycle” carousel |

---

## R — Run

**Goal:** Execute selected plans with the FoXYiZ engine and produce `z/` output.

### How to run

```powershell
cd <installation-root>          # July2/
python BRAHL.py                 # desktop GUI (Run tab)
# or
python f\fEngine2.py            # dev engine
# or
f\Foxyiz2.exe --config fStart.json
```

Config: `f/fStart.json` → `configs` → `y/qoa2/qoa2.json`.

### Key `fStart.json` knobs

| Field | Use |
|-------|-----|
| `tags` | `["Admin"]`, `["XP"]`, `["Smoke"]`, `[]` = all `Run=Y` |
| `thread_count` | `1` for admin/session flows and perf timers; higher for isolated plans |
| `timeout` | Default 6; raise to 10–30 for slow pages |
| `headless` | `false` while debugging locators |

### Tag matching (important)

Plan tags are **semicolon-separated** (`qoa2;Admin;Smoke`). The engine must split on `;` and match any token. Rebuild exe after engine fixes.

### Run exit criteria

- [ ] `Found N plans to execute` matches expected tag filter
- [ ] `z/<timestamp>_<suite>/` folder created
- [ ] `*_zResults.csv` and `*_zDash.html` present

### QAonAir product mapping

| BRAHL phase | In-app area |
|-------------|-------------|
| **Run** | BRAHL **Run** — execute tests (note: some `/run` routes may 404 on qoa2; document in yPAD) |

---

## A — Analyze

**Goal:** Root-cause analysis (RCA) — decide whether each failure is a **test/yPAD defect** or an **application defect**.

### Where to look (in order)

1. **`z/<run>/_errors.csv`** — fast list of failures
2. **`*_zResults.csv`** — per-step `PlanId`, `StepId`, `Input`, `Output`, `Expected`, `Result`
3. **`*_zDash.html`** — interactive dashboard
4. **Artifact folders** — `*.png`, `*.html`, `*.txt` next to failed steps
5. **`python z/zDefects.py`** — defects dashboard (optional)

### RCA decision tree

```
Failure in z/
    │
    ├─ Element not found / timeout
    │     ├─ Wrong locator or UI changed?        → HEAL yD_Common.csv
    │     ├─ Overlay blocking (onboarding modal)? → HEAL dismiss steps / locators
    │     ├─ Wrong page (reuse/cache/session)?   → HEAL navigate + plan order
    │     └─ Element genuinely missing in app  → APP DEFECT (document)
    │
    ├─ Expected text mismatch (xGetText)
    │     ├─ Locator too broad (whole page)?     → HEAL locator; use narrow xpath + empty Expected
    │     └─ App shows wrong copy                → APP DEFECT
    │
    ├─ Auth / wrong user
    │     ├─ DesignId or yD_Secure wrong?      → HEAL designs
    │     └─ App auth bug                        → APP DEFECT
    │
    └─ HTTP 404 / route missing
          ├─ Documented known issue?             → Keep plan; tag Issue
          └─ New regression                      → APP DEFECT
```

### Classify every failure

| Class | Meaning | Action |
|-------|---------|--------|
| **T1 — yPAD** | Locator, step order, Expected, Critical flag, tag, DesignId, timeout | **Heal** y files |
| **T2 — Engine** | Tag filter, action cache, timer, exe stale | Fix `fEngine` / rebuild exe |
| **T3 — Environment** | Credentials, network, browser driver | Fix config / `.env` |
| **A1 — Application** | Broken feature, wrong UX, server error | **Do not** weaken test; file app bug |

### Analyze exit criteria

- [ ] Each red step has a T1/T2/T3/A1 classification
- [ ] Screenshot/HTML confirms actual UI state
- [ ] Reuse/session hypothesis checked (same browser, cached steps)

### AI-assisted analyze

| Method | When |
|--------|------|
| Read `z/` + chat (Cursor agent) | Default — no file writes |
| `python f\fEngine.py --analyze y/qoa2/` | LLM suggestions only (`fEngine.py` with OpenAI) |
| `python z\zDefects.py` | Aggregate view |

### QAonAir product mapping

| BRAHL phase | In-app area |
|-------------|-------------|
| **Analyze** | BRAHL **Analyze** — results, bugs, pass rates |

---

## H — Heal

**Goal:** Fix **T1/T2/T3** issues in yPAD (or engine/config). Leave **A1** tests strict.

### What to heal (priority order)

1. **`yD_Common.csv` / `yD_Secure.csv`** — URLs, locators (smallest change)
2. **`y2Actions.csv`** — step order, `xReuse`, `Critical`, `Expected`, add `xNavigate`; verify with `xGetText` / `xClick` (not `xWaitFor`)
3. **`y1Plans.csv`** — `Run`, `Tags`, `DesignId`, plan order (security before admin, etc.)
4. **`y3Designs.csv`** — only when data matrix changes
5. **`f/fStart.json`** — tags, timeout, thread_count
6. **Engine** — only when RCA proves engine bug (tag split, cache, timer)

### Heal rules for agents

- **Minimal diff** — one root cause per heal batch
- **Match existing style** — same naming, CSV columns, reuse patterns
- **Never “fix” a test** by deleting assertions unless the requirement changed
- **Prefer empty `Expected`** on `xGetText` when verifying presence; avoid exact match on large containers
- **Session-aware plans** — after first login plan, use `xNavigate` not full login reuse
- **Onboarding overlays** — qoa2 shows multi-slide carousel (“Welcome to QAonAir”, “BRAHL Cycle”); dismiss with generic overlay `Next` locators, non-critical steps
- **No secrets in CSV** — credentials in `yD_Secure.csv` or `.env` placeholders only

### Common heal patterns (qoa2 learnings)

| Symptom | Heal |
|---------|------|
| Post-login not on dashboard | Wait for `xp_tracker_widget_locator`; arena is default landing |
| Dashboard check | Verify `social_assistant_locator` (“AI Social Assistant”) |
| Admin tag finds 0 plans | Engine tag split on `;` or rebuild exe |
| Plan 1 passes, 2–5 fail login | Remove redundant `PReuse_Login`; navigate on existing session |
| 27s “freeze” | Wrong onboarding locator; scope to `fixed inset-0` overlay |
| Access denied assertion fails | Narrow locator to `h1`/`h2`; empty `Expected` on `xGetText` |
| Parallel perf timer fails | `thread_count: 1` or per-instance timer in engine |

### Heal exit criteria

- [ ] Re-run failed plan(s) with same tags — green
- [ ] Adjacent plans still pass (no collateral damage)
- [ ] `Summary.md` / session notes updated if team-facing

### AI-assisted heal

| Method | When |
|--------|------|
| Agent edits CSV directly | **Preferred** — reviewable diffs |
| `python f\fEngine.py --heal y/qoa2/` | Bulk heal via LLM (`fEngine.py`); review diffs before commit |

### QAonAir product mapping

| BRAHL phase | In-app area |
|-------------|-------------|
| **Heal** | BRAHL **Heal** — fix failures, improve coverage |

---

## L — Loop

**Goal:** Repeat **Run → Analyze → Heal** in a fixed **three-loop cycle**, then **verify the full suite** and deliver a **standard BRAHL report**. Remaining failures should be **A1 application defects** only.

Every BRAHL cycle an agent or tester completes MUST produce the report in [Standard BRAHL report](#standard-brahl-report) below.

---

### Standard BRAHL cycle (mandatory shape)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  LOOP 1   RUN full in-scope set  →  ANALYZE  →  HEAL                     │
│  LOOP 2   RUN failures from loop 1 only  →  ANALYZE  →  HEAL             │
│  LOOP 3   RUN failures from loop 2 only  →  ANALYZE  →  HEAL             │
│  VERIFY   RUN full in-scope set again (restore all Run=Y)                │
│  REPORT   Publish standard BRAHL report (loops + verify + A1 list)       │
└──────────────────────────────────────────────────────────────────────────┘
```

| Step | What runs | `y1Plans.csv` | Expected duration |
|------|-----------|---------------|-------------------|
| **Loop 1** | Full in-scope set for this cycle | All target plans `Run=Y` | Longest |
| **Loop 2** | Failures from loop 1 only | `Run=N` on passes; `Run=Y` on failures | Shorter |
| **Loop 3** | Failures from loop 2 only | Same shrink | Shortest |
| **Verify** | Full in-scope set again | **Restore all `Run=Y`** on target plans | Catches collateral damage |
| **Report** | No run — write summary | — | — |

**Example:** Loop 1 runs 20 plans → 5 fail. Loop 2 runs **only those 5** → 1 still fails. Loop 3 runs **only that 1** → passes. **Verify** runs all 20 again to confirm heals did not break passing plans.

If loop 1 is **all green**, still run **Verify** (same as loop 1) and report loops 2–3 as *skipped — zero failures*.

---

### Loop protocol (steps 1–3)

```
LOOP 1  RUN  — full in-scope set (all plans you intend to test this cycle, Run=Y)
        ANALYZE — every failure from z/_errors.csv
        HEAL  — fix T1/T2/T3 in yPAD

LOOP 2  RUN  — only PlanIds that FAILED in loop 1 (set Run=N on all passes)
        ANALYZE + HEAL if reds remain

LOOP 3  RUN  — only PlanIds that FAILED in loop 2
        ANALYZE + HEAL if reds remain
```

**Between loops 1–3 — edit `y1Plans.csv`:**

1. Set **`Run=N`** on every plan that **passed** in the last run (`PReuse_*` stays `Run=N` always).
2. Set **`Run=Y`** **only** on plans that **failed** in the last run (keep `Run=Y` until they pass after heal).
3. Do **not** add sentinel plans on loops 2–3 — retest **failures only**.

Example after loop 1 (20 run, 3 fail):

```csv
PWeb_Nav_Shop,...,Y,...        ← failed loop 1; Run=Y for loop 2
PWeb_Ordering_Flow,...,Y,...   ← failed loop 1
PWeb_Admin_Dashboard,...,Y,... ← failed loop 1
PWeb_OpenLanding,...,N,...     ← passed; Run=N
PWeb_VerifyTitle,...,N,...     ← passed; Run=N
```

**Tag filters:** Loop 1 and **Verify** use the same `fStart` config (e.g. `"tags": []` for full suite, or `["Smoke"]` for smoke scope). Loops 2–3 use the same config; only `Run=Y/N` narrows execution.

---

### Final verify (step 4 — required)

After loop 3 is green (or only documented A1 remain), **restore the full suite** and run once more:

1. Set **`Run=Y`** on every plan in the in-scope set (same scope as loop 1).
2. Run the same `fStart` config as loop 1.
3. Confirm **no regressions** — plans that passed in loop 1 must still pass after heals.

```powershell
# After loops 2–3 heals: restore Run=Y on all in-scope plans in y1Plans.csv, then:
python f\fEngine2.py --config f\fStart.json
```

**Verify outcomes:**

| Result | Meaning |
|--------|---------|
| All pass | Cycle complete — publish BRAHL report |
| New failures | Collateral damage from heal — classify, fix, optional mini-loop on new failures, re-verify |
| Same A1 only | Acceptable if documented with evidence; do not weaken tests |

---

### Standard BRAHL report

At the end of **every** BRAHL cycle, produce this report (in chat, PR comment, or ticket). Agents MUST fill all sections and **save it under `z/`** (not `y/`).

### BRAHL report file naming

Run outputs already live in `z/<YYYYMMDD_HHMMSS>_<suite>/` (same timestamp + suite as the engine run folder). The cycle report uses two paths:

| Path | Purpose |
|------|---------|
| `z/<YYYYMMDD_HHMMSS>_<suite>/brahl_report.md` | **Canonical** — next to `{suite}_zDash.html` and `{suite}_zResults.csv` from the **Verify** run |
| `z/brahl_report_<YYYYMMDD_HHMMSS>_<suite>.md` | **Flat index** — easy to glob at `z/` root |

Use the **Verify** run folder timestamp (not Loop 1). Example: `z/20260703_104546_atomic77/brahl_report.md` and `z/brahl_report_20260703_104546_atomic77.md`.

Helpers in `f/fEngine2.py`:

```python
from fEngine2 import write_brahl_report, brahl_report_paths

paths = write_brahl_report(markdown_text, verify_output_dir=r'...\z\20260703_104546_atomic77')
# paths['in_run'], paths['flat']
```

If `brahl_report.md` exists in a run folder, `{suite}_zDash.html` shows a **BRAHL Report** link.

### Capture baseline before Loop 1 (required)

Before the first engine run, record **why** the cycle started, **what yPlans looked like**, and any **uploaded reference documents** so the final report can show delta (e.g. 13 → 24 runnable plans) and trace requirements back to source material.

```python
from fEngine2 import write_brahl_context, snapshot_ypad_plans, write_brahl_report

# Step 0 — before Loop 1
context_path, baseline = write_brahl_context(
    initial_prompt="""<paste the user's request verbatim>""",
    config_path="f/fStart_atomic77.json",
    extra={
        "documents": [
            {
                "name": "Product brief.pdf",
                "path": "Docs/uploads/ivvu-product-brief.pdf",
                "notes": "Route map and auth requirements from customer",
            },
            {
                "name": "API spec.md",
                "path": "Docs/uploads/ivvu-api-notes.md",
            },
        ],
    },
)
# writes z/brahl_context_<YYYYMMDD_HHMMSS>_<suite>.json

# After Verify — include baseline vs endline in markdown
endline = snapshot_ypad_plans("f/fStart_atomic77.json")
write_brahl_report(report_markdown, verify_output_dir=r"...\z\20260703_104546_atomic77")
```

#### Uploaded documents as context

Testers and customers can attach **reference documents** at cycle start (product briefs, route maps, design PDFs, API specs, prior bug lists). These are **not** executed as tests — they inform Build, Analyze, and the final report.

| Method | How |
|--------|-----|
| **BRAHL.py GUI** | Loop tab → Step 0: enter prompt; attach or paste paths to files under `Docs/uploads/` or the project tree |
| **API / script** | Pass `extra={"documents": [...]}` to `write_brahl_context()` (see above) |
| **Agent session** | User `@`-references files in chat; agent copies paths into context JSON at Step 0 |

Each document entry should include at least `name` and `path` (relative to installation root). Optional `notes` field for why the doc matters. The context JSON stores these under `documents`; the BRAHL report **Origin** section should list them alongside the user prompt.

| Artifact | When | Path |
|----------|------|------|
| **Context** | Before Loop 1 | `z/brahl_context_<YYYYMMDD_HHMMSS>_<suite>.json` |
| **Report** | After Verify | `z/<verify_ts>_<suite>/brahl_report.md` + flat index |

The context JSON holds `initialPrompt`, optional `documents`, and `baseline` (full yPlans snapshot). The final report references both and adds `endline` counts after the cycle.

```markdown
# BRAHL Report — <SuiteName> — <YYYY-MM-DD>

**App:** <url>
**Scope:** <e.g. Smoke / full suite / tag Admin> · **Config:** `f/fStart_<name>.json`
**Engine:** fEngine2.py · timeout=<n> · headless=<bool>
**Context file:** `z/brahl_context_<YYYYMMDD_HHMMSS>_<suite>.json`

## Origin — user prompt

> <paste the user's request that started this BRAHL cycle, verbatim>

**Cycle intent:** <one line, e.g. expand API/security/performance plans and run full BRAHL loop>

**Reference documents:** *(optional — from Step 0 context)*

| Document | Path | Notes |
|----------|------|-------|
| | `Docs/uploads/...` | |

## Executive summary (for customer / product owner)

<2–4 sentences: automation status (Verify pass/fail), count of A1 defects documented, whether tests are green while app issues remain>

**Priority fixes before next BRAHL cycle:**

| Priority | Issue | Action |
|----------|-------|--------|
| P1 | | |
| P2 | | |

## yPAD baseline (before Loop 1)

- **yPlans path(s):** `y/<suite>/y1Plans.csv`
- **Snapshot time:** <from context JSON>
- **Counts:** <total> rows · **Run=Y:** <n> · **Run=N:** <n> · reuse: <n>

**Run=Y before BRAHL:**
- `<PlanId>` — …
- …

## yPAD after BRAHL (Verify state)

- **Counts:** <total> rows · **Run=Y:** <n> · **Run=N:** <n>
- **Delta:** +<n> plans added · <n> disabled · tags/API/security/perf added

**Run=Y after BRAHL:**
- …

## Cycle summary

| Step | Plans run | Pass | Fail | Engine time | z/ folder |
|------|-----------|------|------|-------------|-----------|
| Loop 1 | | | | | |
| Loop 2 | | | | | |
| Loop 3 | | | | | |
| Verify | | | | | |

## Loop detail

### Loop 1 — full set
- **Plans executed:** (list PlanIds or count)
- **Failures:** (PlanId, step, one-line RCA) or *none*
- **Heals applied:** (file + change) or *none*

### Loop 2 — failures only
- **Plans executed:** (failed PlanIds from loop 1)
- **Failures:** …
- **Heals applied:** …

### Loop 3 — failures only
- **Plans executed:** (failed PlanIds from loop 2)
- **Failures:** …
- **Heals applied:** …

### Verify — full set (regression guard)
- **Result:** pass / fail
- **Regressions:** (plans that passed loop 1 but failed verify) or *none*

## Classification tally

| Class | Count | Notes |
|-------|-------|-------|
| T1 yPAD | | locators, steps, Expected, Run order |
| T2 Engine | | |
| T3 Environment | | |
| A1 Application | | do not weaken; link artifacts |

## A1 defects (if any)

| PlanId | Step | Evidence | Repro |
|--------|------|----------|-------|
| | | z/…/screenshot | url |

## Customer action plan — next BRAHL run

1. Fix P1 application defects (routes, auth, security) listed above.
2. Re-run BRAHL: Step 0 (prompt + documents) → Verify with same `fStart` config.
3. Expected: Verify green; Issue plans **fail** once routes work (update plans, do not weaken).
4. Publish updated report under `z/` with new Verify timestamp.

## yPAD changes (files touched)

- `y/<suite>/y1Plans.csv` — …
- `y/<suite>/y2Actions.csv` — …
- `y/<suite>/y3Designs.csv` — …

## Verdict

- [ ] Automation complete for in-scope set
- [ ] Verify run green (or A1-only failures documented)
- [ ] Full `Run=Y` restored for CI / user regression

**Dashboard:** `z/<YYYYMMDD_HHMMSS>_<suite>/<suite>_zDash.html`
**BRAHL report:** `z/<YYYYMMDD_HHMMSS>_<suite>/brahl_report.md` · flat: `z/brahl_report_<YYYYMMDD_HHMMSS>_<suite>.md`
```

---

### Command cheat sheet (one cycle)

```powershell
cd <installation-root>

# STEP 0 — capture prompt + yPlans baseline + optional documents (before Loop 1)
python -c "from fEngine2 import write_brahl_context; write_brahl_context('''<user prompt>''', 'f/fStart.json', extra={'documents': [{'name': 'spec.pdf', 'path': 'Docs/uploads/spec.pdf'}]})"

# LOOP 1 — full scope (all Run=Y)
python f\fEngine2.py --config f\fStart.json

# ANALYZE: z/<timestamp>_<suite>/_errors.csv + *_zResults.csv

# HEAL yPAD, then set Run=N on passes / Run=Y on failures

# LOOP 2 — failures only
python f\fEngine2.py --config f\fStart.json

# HEAL, shrink Run=Y to remaining failures

# LOOP 3 — failures only
python f\fEngine2.py --config f\fStart.json

# VERIFY — restore all Run=Y, same config as loop 1
python f\fEngine2.py --config f\fStart.json

# REPORT — fill Standard BRAHL Report template above
```

---

### Stop conditions (definition of done)

| Criterion | Description |
|-----------|-------------|
| **Loops 1–3 complete** | Each failure addressed (fixed or classified A1) |
| **Verify green** | Full in-scope set passes after restores `Run=Y` |
| **Report published** | Standard BRAHL report with **origin prompt**, **baseline yPlans**, **after yPlans**, and loop table — saved under `z/` |
| **App defects only** | Remaining failures documented as A1 with PlanId, step, screenshot, repro URL |
| **No test weakening** | Heal did not remove valid assertions to force green |
| **Exe aligned** | Shipped `Foxyiz2.exe` rebuilt from patched `fEngine2.py` if team uses exe |

### Suggested tag progression (first cycle on a new suite)

```
Smoke → Auth → feature tags → full suite (tags: []) for Loop 1 + Verify
```

For a **quick cycle**, Loop 1 + Verify may use `"tags": ["Smoke"]` with the same report template.

### AI-assisted loop

```powershell
python f\fEngine.py --loop y/qoa2/    # up to 3 run→heal cycles (fEngine.py + OPENAI_API_KEY)
```

Manual loop with Cursor agents is **preferred** — you review each CSV heal and must still run **Verify** + publish the **Standard BRAHL report**.

### QAonAir product mapping

| BRAHL phase | In-app area |
|-------------|-------------|
| **Loop** | BRAHL **Loop** — schedule and repeat the cycle |

---

## qoa2 / QAonAir2 quick reference

| Item | Value |
|------|--------|
| URL | https://qoa2.base44.app/ |
| Workspace suite | `y/qoa2/` |
| Regular user (D1) | test1@itelearn.com |
| Admin user (D2) | test2@itelearn.com |
| Post-login landing | `/arena` + XP tracker widget |
| Dashboard signal | “AI Social Assistant” on Command Center |
| Admin panel | `/admin` — “Admin Panel” |
| Onboarding | Full-screen carousel (Welcome + BRAHL Cycle slides) |
| Known app issues | `/run`, `/analyze` 404; register → login UI |

---

## Agent playbook (checklist)

When invoked on a BRAHL task:

1. **Read** `f/fStart.json`, suite JSON, relevant yPAD rows — do not guess columns.
2. **Run Loop 1** (full in-scope set) or read latest `z/` — never heal without evidence.
3. **Classify** each failure (T1/T2/T3/A1).
4. **Heal** yPAD only for T1; engine for T2; config for T3; document A1.
5. **Run Loops 2–3** on failures only (`Run=N` on passes between loops).
6. **Verify** — restore full `Run=Y`, re-run same scope as Loop 1.
7. **Report** — publish [Standard BRAHL report](#standard-brahl-report) with all loop + verify rows filled.

### Do not

- Add Python yPAD generator scripts unless explicitly requested
- Weaken tests to greenwash app bugs
- Assume exe matches `fEngine2.py` without rebuild
- Skip Verify or the final BRAHL report after a cycle
- Run the full suite on loops 2–3 (failures only)

---

## Human playbook (checklist)

### Starting a new area (e.g. Admin)

- [ ] Explore UI with test2; note locators and overlays
- [ ] Add reuse blocks + tagged plans in y1/y2/yD
- [ ] Run `tags: ["Admin"]` with `thread_count: 1`
- [ ] Analyze `z/`; heal; loop
- [ ] Update `Summary.md` for team handoff

### Completing a BRAHL cycle

- [ ] Loop 1 — full in-scope run + analyze + heal
- [ ] Loop 2 — failures only (skip if loop 1 all green)
- [ ] Loop 3 — failures only (skip if loop 2 all green)
- [ ] Verify — restore all `Run=Y`, full scope re-run
- [ ] Publish Standard BRAHL report (link `z/` folders)

### Before declaring “tests perfect”

- [ ] Loop 1 + Verify pass on `fEngine2.py` for target scope
- [ ] Frozen exe rebuilt and spot-checked (if used in CI)
- [ ] Known A1 issues listed in BRAHL report with plan ids and artifact links
- [ ] No flaky passes from cached reuse or missing navigations

---

## Related documents

| Doc | Purpose |
|-----|---------|
| [FoXYiZ.md](./FoXYiZ.md) | Engine, YPAD contract, heal table |
| [ypad-concepts.md](./ypad-concepts.md) | f, x, y, z model |
| [ai-cli-workflows.md](./ai-cli-workflows.md) | `--build`, `--analyze`, `--heal`, `--loop` |
| [../Summary.md](../Summary.md) | Team handoff — July2 qoa2 status |
| [rules.md](./rules.md) | Agent rules — Playwright exploration, no Python crawlers, BRAHL loop |
| [../BRAHL.py](../BRAHL.py) | Desktop GUI for Build/Run/Analyze/Heal/Loop |
| [../f/Exec.md](../f/Exec.md) | Build `Foxyiz2.exe` |

---

## One-line summary

**BRAHL for FoXYiZ:** Build yPAD → Loop 1 (full) → Loop 2–3 (failures) → Verify (full) → Report — until only the application is wrong.
