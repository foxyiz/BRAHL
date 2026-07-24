# pyUtils — FoXYiZ utilities

**Not engine code** — only `f/fEngine2.py` and `x/xActions.py` live outside this folder.

Run from **`KK/`**:

```powershell
python FoXYiZ\pyUtils\cleaner.py --apply
python FoXYiZ\pyUtils\reset_demo_data.py
python FoXYiZ\pyUtils\sync_personas.py
python FoXYiZ\pyUtils\zBatchDash.py --name wave1 --since 20260716
```

## Packaging tiers

| Tier | Ships with | Scripts |
|------|------------|---------|
| **End-user package root** (`dist/FoXYiZ_user/pyUtils/` or `_pyUtils/`) | Editable Analyze/Heal helpers only | `_paths`, `cleaner`, `yVisualizer`, `zDefects`, `zBatchDash` |
| **Architect** | Full tree | + `site_shot_author.py` / `site_shot_roll.py` (Capture suites → GIF/filmstrip), Arena maintain, … |

**Dist rule:** no `fEngine2.py` or `xActions.py` as shippable source. Run = `FoXYiZ.exe`. Any Python users edit = `pyUtils/` only.


## Keep — runtime (exe + Arena Run)

| Script | Why |
|--------|-----|
| `_paths.py` | Shared paths (`FOXYIZ_ROOT`, suites, `z/`) |
| `fOrchestrate.py` | Tag fan-out / parallel batches (Arena + `fEngine2`) |
| `xCustom.py` | End-user custom actions (`xCustom` in yPAD) |
| `zBatchDash.py` | Multi-run HTML batch dashboard |
| `fGUI.py` | Optional desktop runner GUI |

## Keep — Arena / suite maintain

| Script | Why |
|--------|-----|
| `cleaner.py` | Archive dated `z/` runs → `../archive/cleanup/` |
| `reset_demo_data.py` | Reset Arena seed projects |
| `sync_personas.py` | Personas: `gen_persona_ypad` + `sync_profiles_from_docs` |
| `gen_persona_ypad.py` | Persona yPAD rows (called by sync) |
| `sync_profiles_from_docs.py` | `profiles.js` from `Docs/test-user-data/` |
| `scaffold_app_ypad.py` | Arena “Add challenge” yPAD scaffold (API) |
| `patch_qoa_web_live_v1.py` | Live suite verify gate + locators (idempotent) |
| `gen_journey_ypad.py` | Journey library generator (`--suite qoa_web_live`) |
| `refresh_qoa_web_live.py` | V1 patch + journey regen in one command |
| `fix_y3_journey_locators.py` | Locator append (called by journey gen) |
| `patch_ypad_urls.py` | Post-deploy URL swap for prod smoke |
| `site_shot_author.py` | Generate Capture screenshot yPAD from known routes or `--crawl` |
| `site_shot_roll.py` | PNG sequence → animated GIF + film-strip PNG |

## Optional reports

| Script | Output |
|--------|--------|
| `yVisualizer.py` | `y_visualization.html` — yPAD map |
| `zDefects.py` | `zDefectsDashboard.html` — failure rollup |

## Archived one-offs

Moved to `archive/pyUtils_oneoff/` (not on PATH for agents):

- Heal/fix scripts from past UI migrations
- `author_a77_ypad.py`, `author_ultimate_showdown_ypad.py` (suites already under `y/a77/`, `y/ultimate_showdown/`)

Broken legacy redirects that pointed at removed `u/` were deleted (`y/qoa_web/gen_*.py`, `z/zDefects.py`, `qoa_web/scripts/sync_profiles_from_docs.py`). Use `FoXYiZ/pyUtils/` instead.

HTML reports and `z/*_zDash.html` run output stay out of git — see `.gitignore`.
