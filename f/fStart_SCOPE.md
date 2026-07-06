# fStart configs — qoa_web scope

**Low-code:** copy a journey fStart below, change `"tags"`, run `fEngine2.py`. No Python generators needed for daily runs.

## Release gate (run sequentially)

| Config | Tag filter | ~Plans | Use |
|--------|------------|--------|-----|
| `fStart_qoa_web_verify.json` | `Verify` | 49 | Full verify — every release |
| `fStart_qoa_web_smoke_headless.json` | `Smoke` | 5 | CI / quick gate |
| `fStart_qoa_web_smoke.json` | `Smoke` | 5 | Manual smoke |
| `fStart_qoa_web_smoke_prod.json` | `Smoke` | 5 | Post-deploy (after `patch_ypad_urls`) |

```powershell
cd c:\006\FXYZ\KK
python u/reset_demo_data.py
python f/fEngine2.py --config f/fStart_qoa_web_verify.json
```

## Journey library — parallel batches (~45–85 plans each)

Tags already exist on [`y/qoa_web/y1Plans_journey.csv`](../y/qoa_web/y1Plans_journey.csv). FoXYiZ matches **any** tag in the list (OR).

| Config | Tag | ~Plans |
|--------|-----|--------|
| `fStart_qoa_web_journey_api.json` | `API` | 62 |
| `fStart_qoa_web_journey_brahl.json` | `BRAHL` | 61 |
| `fStart_qoa_web_journey_external.json` | `External` | 45 |
| `fStart_qoa_web_journey_cost.json` | `Cost` | 67 |
| `fStart_qoa_web_journey_foxyiz.json` | `FoXYiZ` | 78 |
| `fStart_qoa_web_journey_qahunter.json` | `QA_Hunter` | 25 |
| `fStart_qoa_web_journey_build.json` | `Build` | 85 |
| `fStart_qoa_web_journey_nav.json` | `Nav` | 115 |
| `fStart_qoa_web_journey_atomic77.json` | `Atomic77` | 181 |
| `fStart_qoa_web_journey_panel.json` | `Panel` | 139 |

**Overnight only:** `fStart_qoa_web_regression.json` (`Journey` tag, all 800 plans).

### Run 6 parallel workers (demo subset)

Prerequisites: `python qoa_web/run_local.py` on :8765, `python u/reset_demo_data.py`.

Open **6 terminals** (or paste each line):

```powershell
cd c:\006\FXYZ\KK
python f/fEngine2.py --config f/fStart_qoa_web_journey_api.json
python f/fEngine2.py --config f/fStart_qoa_web_journey_brahl.json
python f/fEngine2.py --config f/fStart_qoa_web_journey_external.json
python f/fEngine2.py --config f/fStart_qoa_web_journey_cost.json
python f/fEngine2.py --config f/fStart_qoa_web_journey_foxyiz.json
python f/fEngine2.py --config f/fStart_qoa_web_journey_qahunter.json
```

Each run writes its own `z/<timestamp>_qoa_web/` dashboard. Wall time ≈ longest batch, not sum of all 800.

**Tip:** redirect stdout so you keep one log per terminal:

```powershell
python f/fEngine2.py --config f/fStart_qoa_web_journey_api.json > z/parallel_demo_api.log 2>&1
```

When all terminals finish, build one **batch dashboard** (pass/fail + parallel vs sequential time):

```powershell
python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
# → z/zDash_batch_parallel_demo.html
```

Or point at run folders directly:

```powershell
python u/zBatchDash.py --name journey_wave1 --since 20260705_1118
python u/zBatchDash.py --name custom --runs z/20260705_111807_qoa_web z/20260705_111809_qoa_web
```

### Split a large bucket without code

In Excel: add sub-tags to `Tags` column (e.g. `Nav_A`, `Nav_B`), copy fStart, set `"tags": ["Nav_A"]`.

### New batch template

Copy any journey fStart JSON; change only `"tags": ["YourTag"]`.

---

Other `f/fStart*.json` files are for **other apps** (qoa2, sunshine, ivvu, atomic77). Listed in `.cursorignore`.
