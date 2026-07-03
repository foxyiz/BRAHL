# FoXYiZ / BRAHL / qoa_web — Team Summary

**Handoff index for `KK/`** · Last updated: 2026-07-03

**Formula:** `f(x, y) = z` — engine + yPAD → results in `z/`.

---

## Doc map (read this first)

| Doc | Use when |
|-----|----------|
| **Summary.md** (this file) | Handoff, commands, suite status, doc index |
| [Docs/BRAHL.md](Docs/BRAHL.md) | Full BRAHL cycle, reports, Step 0, agent skill |
| [Docs/rules.md](Docs/rules.md) | Agent rules: Playwright-only explore, heal loops, edit scope |
| [Docs/FoXYiZ.md](Docs/FoXYiZ.md) | yPAD columns, xActions, tags, CLI flags |
| [Docs/README.md](Docs/README.md) | End-user FoXYiZ install & quick start |
| [qoa_web/README.md](qoa_web/README.md) | Local BRAHL web app quick start |
| [qoa_web/AVATARS_AND_BUILD.md](qoa_web/AVATARS_AND_BUILD.md) | Client vs HITL, Build chat, budget, APIs |
| [qoa_web/PRD.md](qoa_web/PRD.md) | Product requirements, cloud worker architecture |
| [qoa_web/RESEARCH.md](qoa_web/RESEARCH.md) | Why qoa2 cannot run FoXYiZ in Base44 |
| [.cursor/rules/token-efficiency.md](.cursor/rules/token-efficiency.md) | Cursor agent token discipline |
| [f/Exec.md](f/Exec.md) | Exe build notes |

**Rule:** Detail lives in linked docs. This file stays short — update here when suite status or qoa_web changes.

---

## Workspace layout

```
KK/
  BRAHL.py              ← desktop GUI (Build/Run/Analyze/Heal/Loop)
  Summary.md            ← you are here
  f/fEngine2.py         ← engine source
  f/Foxyiz2.exe         ← rebuild after x/xActions.py changes
  f/fStart*.json        ← run configs (tags, timeout, headless)
  x/xActions.py         ← UI/API actions (no xWaitFor)
  y/<suite>/            ← y1Plans, y2Actions, y3Designs, *.json
  z/                    ← run output (*_zResults, *_zDash, brahl_report.md)
  qoa_web/              ← local web UI + API (port 8765)
  Docs/                 ← BRAHL, rules, FoXYiZ
```

---

## Quick run

From **`KK/`**:

```powershell
# BRAHL desktop
python BRAHL.py

# qoa_web (browser UI)
python qoa_web/run_local.py          # → http://127.0.0.1:8765

# Sunshine smoke / full
python f\fEngine2.py --config f\fStart_sunshine_smoke.json
python f\fEngine2.py --config f\fStart_sunshine.json

# qoa2 full / smoke / admin
python f\fEngine2.py --config f\fStart.json
python f\fEngine2.py --config f\fStart_smoke.json
python f\fEngine2.py --config f\fStart_admin.json

# qoa_web self-test (server must be running)
python f\fEngine2.py --config f\fStart_qoa_web_smoke_headless.json   # 5 plans
python f\fEngine2.py --config f\fStart_qoa_web_verify.json           # 60 plans
```

| Config | Suite | Tags | Plans |
|--------|-------|------|-------|
| `fStart_sunshine_smoke.json` | sunshine | Smoke | 5 |
| `fStart_sunshine.json` | sunshine | all | 26 |
| `fStart_smoke.json` | qoa2 | Smoke | subset |
| `fStart_admin.json` | qoa2 | Admin | 5 |
| `fStart.json` | qoa2 | all | ~81 |
| `fStart_qoa_web_smoke*.json` | qoa_web | Smoke | 5 |
| `fStart_qoa_web_verify.json` | qoa_web | all Run=Y | 60 |

Defaults for local heal loops: **`timeout: 6`**, **`headless: false`**, **`thread_count: 1`**.

---

## FoXYiZ essentials

- **yPAD:** `y1Plans` (what), `y2Actions` (how), `y3Designs` (data). No Python CSV generators.
- **Expected:** exact string match — use empty `Expected` for presence-only checks, or full UI text.
- **No `xWaitFor`** — use `xGetText`, `xClick`, `xNavigate` (honor `timeout` in fStart).
- **Reuse:** after `xReuse OpenSite`, always **`xNavigate base_url`** in parent plan (session reset).
- **Explore:** Playwright MCP only — no new `explore_*.py` crawlers ([rules.md](Docs/rules.md)).
- **Heal loops 2–3:** `Run=N` on passes, `Run=Y` only on failures; full `Run=Y` for user/CI Verify.

### xActions (July 2026)

| Change | Effect |
|--------|--------|
| Removed `extra_wait_seconds`, headless 10s floor | Respects fStart `timeout` |
| Retries | 0 local, 1 when headless |
| `xWaitFor` removed | Heal old steps to xGetText/xClick |

Rebuild **`f/Foxyiz2.exe`** after pulling `xActions.py`.

---

## qoa_web (local BRAHL web — **v1.0**)

**URL:** http://127.0.0.1:8765 · **Restart server** after API/UI changes.

### Roles

| Avatar | Project UX | Build |
|--------|------------|-------|
| **Client** | Top bar + Build dropdown synced; **Add project** modal | AI chat, checklist, budget, HITL roster |
| **HITL** | Top bar + dropdown + browse grid (filter/sort/compact) | Join project, upload report |

### Phases (nav)

Build · Run · Analyze · Heal · Loop · **BRAHL** — project-scoped with **phase progress bar**, locked CTAs when no project.

### v1.0 highlights

- **Heal:** shrink to failures / restore Run=Y (BRAHL.py parity)
- **Loop:** Step 0, Loop 1/2/3, Verify (auto shrink/restore), cycle history, generate report
- **Run:** suite picker + fStart config + live job log
- **API:** `/api/version`, `/api/ypad/shrink`, `/api/ypad/restore`, cycle history
- **MCP:** `python qoa_web/mcp/server.py` — `foxyiz_run`, `foxyiz_analyze`, etc.

### Verify status

| Run | Result | Output |
|-----|--------|--------|
| `z/20260703_155434_qoa_web/` | **60/60** | **v1.0 release** — Client + HITL + brahl_report |
| `z/20260703_154520_qoa_web/` | 50/50 | v1.0 core features |

Launch guide: [qoa_web/LAUNCH.md](qoa_web/LAUNCH.md) · Changelog: [qoa_web/CHANGELOG.md](qoa_web/CHANGELOG.md)

Detail: [AVATARS_AND_BUILD.md](qoa_web/AVATARS_AND_BUILD.md) · Cloud plan: [PRD.md](qoa_web/PRD.md)

---

## External apps under test

| App | URL | Suite |
|-----|-----|--------|
| QAonAir2 | https://qoa2.base44.app/ | `y/qoa2/` |
| Sunshine | https://gosunshine.base44.app/ | `y/sunshine/` |
| qoa_web (local) | http://127.0.0.1:8765 | `y/qoa_web/` |

### Sunshine (`y/sunshine/`)

- Reuse: `PReuse_sunshine_OpenSite` → always `xNavigate base_url` in step 2.
- Admin PIN `5566`; post-PIN may redirect to login (A1) — verify `admin_post_pin_locator`.
- **Latest:** full **26/26** (`z/20260703_101034_sunshine/`), smoke **5/5**.

### qoa2 (`y/qoa2/`)

- Personas: D1 `test1@itelearn.com`, D2 `test2@itelearn.com` / `test@itelearn` ([Common/yD_Secure.csv](y/qoa2/Common/yD_Secure.csv)).
- Post-login → `/arena`; dismiss onboarding Next ×4.
- Admin tag: 5 plans, reference **5/5** (`z/20260702_125641_qoa2/`).
- **Known:** BRAHL Run/Analyze routes 404 in cloud (engine not on Base44).

---

## BRAHL loop (condensed)

```
Build (y/) → Run (f/) → Analyze (z/) → Heal (y/) → Loop → Verify → Report
```

| Loop | Scope |
|------|--------|
| 1 | Full tagged / all Run=Y |
| 2–3 | Run=Y failures only; Run=N on passes |
| Verify | Full Run=Y restored; user or CI |

Reports: `z/<timestamp>_<suite>/brahl_report.md` + flat `z/brahl_report_<ts>_<suite>.md`.

---

## Known issues

| Issue | Where | Workaround |
|-------|--------|------------|
| Nested reuse cache | Engine | Explicit `xNavigate base_url` after reuse |
| Exact Expected match | All suites | Empty Expected or full string |
| Sunshine PIN → login | sunshine | A1; tag Issue on strict dashboard plan |
| qoa2 Run/Analyze 404 | qoa2 cloud | Use qoa_web local engine |
| qoa_web stale API | local dev | Restart `run_local.py` |
| Cosmetic "Failed: 1" on nested reuse | Engine CSV | Ignore if plan passed |

---

## Build exe

```powershell
cd c:\006\FXYZ\KK
pip install -r f\requirements.txt
pyinstaller --onefile --name Foxyiz2 --paths . ^
  --add-data "x\xActions.py;x" --add-data "z\zDash_template.html;z" ^
  --hidden-import pandas --hidden-import x.xActions ^
  --hidden-import selenium --hidden-import webdriver_manager ^
  --hidden-import dotenv --hidden-import multiprocessing.spawn ^
  f\fEngine2.py
copy dist\Foxyiz2.exe f\Foxyiz2.exe
```

---

## Authoring workflow

1. Explore with **Playwright MCP**.
2. Edit **`y/<suite>/`** CSVs + suite JSON.
3. Run tagged subset via **`f/fStart_*.json`**.
4. Analyze **`z/_errors.csv`**, **`*_zDash.html`**.
5. Heal yPAD; shrink Run=Y for loops 2–3.
6. User runs full Verify; link report in qoa_web **BRAHL** tab if testing qoa_web.

---

*Apps: qoa2.base44.app · gosunshine.base44.app · qoa_web @ :8765*
