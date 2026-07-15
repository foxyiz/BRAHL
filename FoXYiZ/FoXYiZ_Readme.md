# FoXYiZ — Complete guide (BRAHL as QA agent)

**One doc** for humans and AI agents working the FoXYiZ engine. Spelling: **FoXYiZ** · **BRAHL** · **yPAD**.

**Formula:** `f(x, y) = z`

| Symbol | Meaning |
|--------|---------|
| **f** | Engine — `f/fEngine2.py`, `fStart_*.json`, `fOrchestrate.py` |
| **x** | Capabilities — `xUI`, `xAPI`, `xMath`, `xJSON`, `xReuse`, … |
| **y** | yPAD suites — plans, actions, designs under `y/<suite>/` |
| **z** | Results — `*_zResults.csv`, `*_zDash.html`, `_errors.csv` |

**BRAHL** is how FoXYiZ behaves as a **QA agent** for the whole lifecycle:

```
Build (yPAD) → Run (engine) → Analyze (z/) → Heal (yPAD) → Loop → Verify → report
```

| Product (qoa_web Arena) | FoXYiZ |
|-------------------------|--------|
| Build / Analyze / Heal tabs | Author & fix **y/** (AI may assist) |
| Run / Loop | **fEngine2 only** — never an LLM |
| BRAHL report | Launch readiness from latest `z/` |

Arena UI lives next door in `../qoa_web/`. This folder is the engine package.

---

## 1. Folder layout (current)

```
KK/
  FoXYiZ/                 ← you are here
    f/                    engine + fStarts
    x/                    action handlers
    y/                    yPAD suites (Math, nalanda_app, qoa_web_live, …)
    z/                    run output (local; huge — keep out of AI context)
    pyUtils/              cleaner, sync, dashboards
  qoa_web/                BRAHL web UI + API (:8765)
  Docs/                   deep references (linked below)
  archive/                ephemeral archives (never load into agent context)
```

Short paths in configs stay `f/…`, `y/…`, `z/…`. The Arena API resolves them via `FOXYIZ_ROOT` (= this folder). Optional: `$env:FOXYIZ_ROOT = "…"`.

### From `KK/`

```powershell
python qoa_web\run_local.py
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
python FoXYiZ\pyUtils\cleaner.py --apply
```

Lean day-to-day smoke: **Math** / **nalanda_app**. Full Arena UX gate: `y/qoa_web_live` + `f/fStart_qoa_web_live_verify.json`.

---

## 2. BRAHL as QA agent — phase cheat sheet

| Phase | Who runs it | Job | AI? |
|-------|-------------|-----|-----|
| **Build** | Human / agent | Explore app → write y1/y2/y3 + suite JSON + tags + reuse | Assist |
| **Run** | FoXYiZ | Execute `Run=Y` plans filtered by fStart tags | **Never** |
| **Analyze** | Human / agent | Read `z/_errors.csv` + failing rows in `*_zResults.csv`; classify T1–T3 vs A1 | Assist |
| **Heal** | Human / agent | Minimal yPAD fixes for T1–T3; leave A1 strict | Assist |
| **Loop** | FoXYiZ + Arena | Shrink `Run=Y` to failures → re-run → restore → Verify | **Never** |
| **Report** | Human / agent | Go/No-Go from `brahl_report.md` + plan-level stats | Q&A only |

### Loop protocol (required)

```
Loop 1   full Run=Y → Analyze → Heal
Loop 2   Run=N on passes → failures only → Heal
Loop 3   remaining failures → Heal
Verify   restore all Run=Y → full run → BRAHL report
```

Do **not** declare done after a single green Run. Do **not** weaken Expected / assertions to hide **A1** app defects.

### Failure classes

| Code | Meaning | Action |
|------|---------|--------|
| **T1** | yPAD (locator, Expected, step order, DesignId, tag) | Heal CSV |
| **T2** | Config / timeout / fStart | Fix fStart or timeout |
| **T3** | Engine / action gap | Note; escalate if needed |
| **A1** | Real product bug | Keep test strict; list in report |

---

## 3. Typical skills (what agents should know)

Treat these as the **skill pack**. Prefer them over inventing new scripts.

### 3.1 Core FoXYiZ skill

- Author / edit **yPAD only** unless user asks for engine changes.
- Run with `fEngine2` + the right `fStart`.
- Heal from `z/` evidence, one plan at a time.
- Tag smoke first, then feature tags, then verify.

### 3.2 BRAHL lifecycle skill

- Know Build → Run → Analyze → Heal → Loop → Verify.
- Keep Run/Loop free of LLMs.
- Plan-level pass/fail counts (not raw action rows).

### 3.3 Exploration skill (Playwright MCP only)

- Discover routes, headings, buttons, stable locators with **browser_* tools**.
- Update `y3Designs` / `yD_*.csv` — do **not** create `explore_*.py` / scrapers.
- Prefer `css=` / `xpath=` / `id=` locators after live snapshot.

### 3.4 yPAD editing skill

- **y1Plans** — what runs (`PlanId`, `DesignId`, `Run`, `Tags`).
- **y2Actions** — how (`ActionType`, `ActionName`, `Input`, `Expected`, `Critical`).
- **y3Designs** — data & locators (columns D1, D2, …).
- Suite JSON `input_files` merges lists in order.

### 3.5 xReuse skill

- Every web suite: `PReuse_<Suite>_OpenSite` with `Run=N`.
- Unique ID per suite (never share bare `PReuse_OpenSite`).
- After reuse, browser may sit on the last page → reset with `xNavigate` when unsure.
- Callable via `xReuse,<PlanId>`.

### 3.6 Action skills (common)

| Family | Use for | Notes |
|--------|---------|--------|
| **xUI** | Browser | `xNavigate`, `xClick`, `xType`, `xGetText`, … — auto-wait via fStart `timeout` |
| **xAPI** | HTTP | `xGet` / `xPost` + Expected status |
| **xMath** | Pure calc | Math suite / helpers |
| **xJSON** | API body | Validate / extract / compare last response |
| **xReuse** | Inline plan | Session shortcuts |

**Do not use `xWaitFor`** — removed / flaky. Prefer `xNavigate`, `xGetText`, or click/type with timeout.

### 3.7 Orchestration skill

- One suite + `thread_count: 1` + tags → **OR** filter.
- One suite + `thread_count > 1` + 2+ tags → **tag fan-out** (`fOrchestrate`) → `z/zDash_batch_*.html`.
- Arena: multi-chip **Run parallel**.

### 3.8 Maintenance skill (`pyUtils/`)

| Script | Purpose |
|--------|---------|
| `cleaner.py` | Move dated `z/` noise → `archive/cleanup/` |
| `sync_personas.py` | Docs personas → yPAD / profiles |
| `reset_demo_data.py` | Reset Arena seed projects |
| `zBatchDash.py` / `zDefects.py` / `yVisualizer.py` | Reports under `pyUtils/` |

---

## 4. Memory usage (humans + AI)

### 4.1 What “memory” means here

| Kind | Where | Purpose |
|------|--------|---------|
| **Agent session memory** | `qoa_web/MEMORY.md` | Read first (≤80 lines); stop unless task needs more |
| **Handoff memory** | `Docs/HANDOFF.md` | New machine / cold start |
| **Project memory** | Arena project + `brahl_context_*` | Purpose / Step 0 origin |
| **AI usage meter** | `qoa_web/data/ai_usage.json` + Wallet ($) | BYOK / hosted caps |
| **Run memory** | `FoXYiZ/z/<run>/` | Evidence — **cite paths**, do not paste blobs |
| **Archive** | `KK/archive/` | Dead weight — **never** put in context |

### 4.2 Read order (token-smart)

1. `qoa_web/MEMORY.md`
2. This file (`FoXYiZ/FoXYiZ_Readme.md`) if doing engine / yPAD / heal
3. One targeted CSV / fStart / single `z/` error row
4. Deep docs only when stuck: `Docs/BRAHL.md`, `Docs/FoXYiZ.md`

### 4.3 Never load into context

- `archive/**`
- Full `FoXYiZ/z/**` HTML dashboards or whole `*_zResults.csv`
- Fat journey CSVs (~800 plans) unless user explicitly asks for journey work
- Agent transcripts unless the user cites a chat

`.cursorignore` already excludes `archive/` and `FoXYiZ/z/` — trust it.

### 4.4 In-app AI budgets (`ai_assist`)

| Role | Doc chars | History | max completion |
|------|-----------|---------|----------------|
| Planner | ~2.5k | 4 | 600 |
| Build / BRAHL chat | ~3.5k | 6 | 800 |
| Analyze / Heal | ~4k | 0–2 | 1000 |
| Atomic 77 | ~2k | 4 | 500 |

Packed prompts should stay slim: **AI_GUARDRAILS** + **BRAHL_PROMPT** (+ short “My docs”). Prefer FAQ / offline templates when no key.

---

## 5. Efficient yPAD (practical patterns)

### 5.1 File contract

**y1Plans.csv** — `PlanId, PlanName, DesignId, Run, Tags, Output`

- `Run=Y` execute · `Run=N` skip (reuse / optional)
- Tags: semicolon-separated (`Smoke;Verify;Build`)
- DesignId: `D1` or `D1;D2` for multi-persona

**y2Actions.csv** — `PlanId, StepId, StepInfo, ActionType, ActionName, Input, Output, Expected, Critical`

- `Input` tokens resolve from Designs `DataName`
- `Expected`: exact string match; empty = presence-only on `xGetText`
- `Critical=y` stops plan on fail

**y3Designs.csv / yD_*.csv** — `Type, DataName, D1, D2, …`

- Locators: `css=…`, `xpath=…`, `id=…`
- URLs in designs: plain `&` in query strings (not HTML entities)

### 5.2 Efficiency rules that save the most time

1. **Reuse blocks** — OpenSite / Login once; every UI plan starts with `xReuse`.
2. **Tags over giant suites** — iterate with `Smoke` or one feature tag; verify only when asked.
3. **One concern per plan** — smaller plans heal faster and parallelize cleaner.
4. **Session-aware** — after login, `xNavigate` to the page under test; don’t rely on leftover URL.
5. **Narrow locators** — `css=h1` beats whole-page containers; empty Expected for presence.
6. **No Python CSV generators for daily edits** — edit CSVs directly (unless user asks for a generator).
7. **Don’t sync personas after manual gate edits** — `sync_personas.py` can overwrite carefully tuned verify rows.
8. **Lean suites for agent loops** — prefer `y/Math/` and `y/nalanda_app/` over full journey libraries.
9. **Heal one failure at a time** — patch → re-run that plan or smoke → then restore/verify.
10. **A1 defect plans** — Issue / Link / Security tags that **pass when the bug is present**; document in report.

### 5.3 Size ladder (pick smallest that proves the fix)

| Goal | Typical run |
|------|-------------|
| One locator | Single plan or Smoke |
| UI patch on Arena | `qoa_web_live` Verify (~58) only if needed |
| Day-to-day confidence | Math smoke |
| Release | User-driven Verify gate |
| Journey / overnight | Explicit user ask only |

### 5.4 Suite bootstrap checklist

1. Explore with Playwright MCP  
2. `y/<App>/<App>.json` + y1 / y2 / y3 (+ Common designs)  
3. `PReuse_<App>_OpenSite` (`Run=N`)  
4. Tag Smoke + feature tags  
5. `f/fStart_<App>_smoke.json` then verify fStart  
6. Loop → Verify → BRAHL report  

---

## 6. Best AI practices & rules

### 6.1 Always

- Spell **BRAHL** and **FoXYiZ** correctly.
- Scope to the active suite / project (name, URL, purpose, latest run path).
- Truncate answers; bullets; **one** primary next step.
- Cite `z/<run>/` paths + one failing PlanId/StepId — don’t dump logs.
- Prefer Math / nalanda for agent iteration.

### 6.2 Never

- Put an LLM into **Run** or **Loop** execution.
- Paste entire yPAD CSVs or zDash HTML into chat / prompts.
- Weaken assertions to force green (especially A1).
- Create `explore_*.py` / scrapers — use Playwright MCP.
- Default to full verify / journey / parallel 4-job noise for small questions.
- Commit secrets; put passwords in PlanNames.
- Load `archive/**` or whole `FoXYiZ/z/**` into context.
- Modify `fEngine2.py` / `xActions.py` unless the user asks.

### 6.3 Default edit scope

| Edit freely | Touch only if asked |
|-------------|---------------------|
| `y/**/*.csv`, `y/**/*.json` | `f/fEngine2.py`, `x/**` |
| `f/fStart*.json` | Exe builds, frozen binaries |
| `pyUtils/` helpers | New exploration scripts |

### 6.4 Response discipline (agents)

| Task tier | Response |
|-----------|----------|
| Question | ≤15 lines; minimal tools |
| Single fix | 1–3 bullets + smoke result |
| Heal cycle | Short summary + remaining fails table |
| Release | Structured report; still no log paste |

In-app AI: ≤120 words unless user asks for a table; never invent locators/URLs not in context; never claim to have executed FoXYiZ — point to **Run** / **Loop**.

### 6.5 BYOK / hosted

- Desktop: `OPENAI_API_KEY` in `FoXYiZ/f/.env` (platform pays $0).
- Hosted: enforce wallet + monthly caps via `chat_metered` — never bypass.
- Without a key: use offline FAQ / templates.

### 6.6 Session hygiene

Every ~30 minutes or end of work:

```powershell
python FoXYiZ\pyUtils\cleaner.py          # dry-run
python FoXYiZ\pyUtils\cleaner.py --apply  # archive dated z/
```

Safe to delete `archive/cleanup/` anytime. Keep `MEMORY.md` and verify counts in sync when gate scope changes.

---

## 7. Commands pocket card

```powershell
cd c:\006\FXYZ\KK

# Arena
python qoa_web\run_local.py
# http://127.0.0.1:8765/app?demo=1

# Lean engine smoke
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json

# Tag parallel (example)
python FoXYiZ\f\fOrchestrate.py --config f\fStart_Math_parallel_tags.json

# Live Arena V1 gate (server must be up)
python FoXYiZ\pyUtils\reset_demo_data.py
python FoXYiZ\f\fEngine2.py --config f\fStart_qoa_web_live_verify.json

# Hygiene
python FoXYiZ\pyUtils\cleaner.py --apply
```

Configs still use short paths (`f\…`) — run with cwd such that FoXYiZ roots resolve (Arena does this automatically; CLI: run engine from paths that include `FoXYiZ` on `FOXYIZ_ROOT`, or `cd FoXYiZ` then `python f\fEngine2.py --config f\…`).

---

## 8. Where deep detail still lives

This README consolidates day-to-day practice. For long tables and history:

| Doc | Use when |
|-----|----------|
| [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) | Session start (always) |
| [../Docs/BRAHL_PROMPT.md](../Docs/BRAHL_PROMPT.md) | Slim in-app BRAHL |
| [../Docs/AI_GUARDRAILS.md](../Docs/AI_GUARDRAILS.md) | Token budgets |
| [../Docs/BRAHL.md](../Docs/BRAHL.md) | Full loop / A1 / heal tables |
| [../Docs/FoXYiZ.md](../Docs/FoXYiZ.md) | Full yPAD + action encyclopedia |
| [../Docs/rules.md](../Docs/rules.md) | Explore vs automate boundaries |
| [../Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) | End-of-session checklist |
| [../Docs/BRAHL_DESKTOP_BYOK.md](../Docs/BRAHL_DESKTOP_BYOK.md) | OpenAI key / hosted quotas |
| [f/fStart_SCOPE.md](./f/fStart_SCOPE.md) | Which fStart for smoke / verify / journey |
| [pyUtils/README.md](./pyUtils/README.md) | Utility scripts |
| [../.cursor/rules/ai-token-hygiene.mdc](../.cursor/rules/ai-token-hygiene.mdc) | Cursor always-on hygiene |

---

## One-line summary

**FoXYiZ runs `f(x,y)=z`; BRAHL is the QA-agent loop around it — Build/Heal with thin AI, Run/Loop with the engine only, keep yPAD lean and tagged, and never feed archive or fat `z/` into memory.**
