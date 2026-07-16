# fStart configs — qoa_web scope

**Low-code:** copy a journey fStart below, change `"tags"`, run `fEngine2.py` (or arena **Run** chips). No Python generators needed for daily runs.

## Tag fan-out vs OR filter

| `thread_count` | `tags` | Behavior |
|----------------|--------|----------|
| `1` | 2+ tags | **OR** filter (plans matching any tag) — classic FoXYiZ |
| `>1` | 2+ tags, one suite in `configs` | **Tag fan-out** via [`pyUtils/fOrchestrate.py`](../pyUtils/fOrchestrate.py): one tag per worker, then `z/zDash_batch_*.html` |
| `>1` | multiple yPAD paths in `configs` | Parallel suites (unchanged) |

Example (Math): `f/fStart/Math_parallel_tags.json` — `thread_count: 2`, `tags: ["Smoke","Math"]`.  
Example (qoa_web): `f/fStart/qoa_web_parallel_tags.json` — `tags: ["Smoke","API"]`.

Arena: select multiple fStart chips → **Run parallel** (multi-config batch + batch zDash). Future **FoXYiZ.exe** entry = orchestrator.

## Screen capture (images / video)

Optional `capture` block in any `f/fStart/*.json` — applies to the whole run (FoXYiZ engine, not AI).

```json
"capture": {
  "image": "on_fail",
  "video": "off",
  "video_fps": 2,
  "subdir": ""
}
```

| Field | Values | Meaning |
|-------|--------|---------|
| `image` | `off` · `on_fail` · `every_step` · `on_pass` | Auto PNG after UI steps |
| `video` | `off` · `on_fail` · `every_step` · `plan` | Frame sequence (`plan` = xOpenBrowser → xCloseBrowser) |
| `video_fps` | 1–10 | Frames per second for video modes |
| `subdir` | e.g. `captures` | Folder under each plan’s `z/` run dir |

**yPAD explicit steps** (first step in a plan, after browser open):

```csv
PlanId,StepId,StepInfo,ActionType,ActionName,Input,Output,Expected,Critical
PMyPlan,0,Capture baseline,xCapture,xCaptureImage,baseline,,,n
PMyPlan,0b,Record flow,xCapture,xCaptureVideoStart,run1,,,n
…
PMyPlan,99,Stop recording,xCapture,xCaptureVideoStop,,,,n
```

Artifacts land in `z/<timestamp>_<plan>/` and appear as `[Link to …]` in zResults / zDash.

## Release gate (run sequentially)

| Config | Tag filter | ~Plans | Use |
|--------|------------|--------|-----|
| `qoa_web_verify.json` | `Verify` | 49 | Full verify — every release (`y/qoa_web`) |
| `qoa_web_live_verify.json` | `Verify` | ~58 | **Live Arena V1** — current `/app` UX (`y/qoa_web_live`) |
| `qoa_web_live_smoke.json` | `Smoke` | ~20 | **Live Arena smoke** — BRAHL day-to-day (`y/qoa_web_live`) |
| `qoa_web_smoke_headless.json` | `Smoke` | 5 | CI / quick gate (classic `y/qoa_web`) |
| `qoa_web_smoke.json` | `Smoke` | 5 | Manual smoke |
| `qoa_web_smoke_prod.json` | `Smoke` | 5 | Post-deploy (after `patch_ypad_urls`) |

```powershell
cd c:\006\FXYZ\KK
python pyUtils/reset_demo_data.py
python f/fEngine2.py --config f/fStart/qoa_web_verify.json
```

## Journey library — parallel batches (~45–85 plans each)

Tags already exist on [`y/qoa_web/y1Plans_journey.csv`](../y/qoa_web/y1Plans_journey.csv). FoXYiZ matches **any** tag in the list (OR).

| Config | Tag | ~Plans |
|--------|-----|--------|
| `qoa_web_journey_api.json` | `API` | 62 |
| `qoa_web_journey_brahl.json` | `BRAHL` | 61 |
| `qoa_web_journey_external.json` | `External` | 45 |
| `qoa_web_journey_cost.json` | `Cost` | 67 |
| `qoa_web_journey_foxyiz.json` | `FoXYiZ` | 78 |
| `qoa_web_journey_qahunter.json` | `QA_Hunter` | 25 |
| `qoa_web_journey_build.json` | `Build` | 85 |
| `qoa_web_journey_nav.json` | `Nav` | 115 |
| `qoa_web_journey_atomic77.json` | `Atomic77` | 181 |
| `qoa_web_journey_panel.json` | `Panel` | 139 |

**Overnight only:** `qoa_web_regression.json` (`Journey` tag, all 800 plans).

### Run 6 parallel workers (demo subset)

Prerequisites: `python qoa_web/run_local.py` on :8765, `python pyUtils/reset_demo_data.py`.

Open **6 terminals** (or paste each line):

```powershell
cd c:\006\FXYZ\KK
python f/fEngine2.py --config f/fStart/qoa_web_journey_api.json
python f/fEngine2.py --config f/fStart/qoa_web_journey_brahl.json
python f/fEngine2.py --config f/fStart/qoa_web_journey_external.json
python f/fEngine2.py --config f/fStart/qoa_web_journey_cost.json
python f/fEngine2.py --config f/fStart/qoa_web_journey_foxyiz.json
python f/fEngine2.py --config f/fStart/qoa_web_journey_qahunter.json
```

Each run writes its own `z/<timestamp>_qoa_web/` dashboard. Wall time ≈ longest batch, not sum of all 800.

**Tip:** redirect stdout so you keep one log per terminal:

```powershell
python f/fEngine2.py --config f/fStart/qoa_web_journey_api.json > z/parallel_demo_api.log 2>&1
```

When all terminals finish, build one **batch dashboard** (pass/fail + parallel vs sequential time):

```powershell
python pyUtils/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
# → z/zDash_batch_parallel_demo.html
```

Or point at run folders directly:

```powershell
python pyUtils/zBatchDash.py --name journey_wave1 --since 20260705_1118
python pyUtils/zBatchDash.py --name custom --runs z/20260705_111807_qoa_web z/20260705_111809_qoa_web
```

### Split a large bucket without code

In Excel: add sub-tags to `Tags` column (e.g. `Nav_A`, `Nav_B`), copy fStart, set `"tags": ["Nav_A"]`.

### New batch template

Copy any journey fStart JSON; change only `"tags": ["YourTag"]`.

---

Other `f/fStart/*.json` files are for **other apps** (qoa2, sunshine, ivvu, atomic77). Listed in `.cursorignore`.
