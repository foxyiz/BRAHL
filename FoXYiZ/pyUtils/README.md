# pyUtils — FoXYiZ utilities

**Not engine code** — only `f/fEngine2.py` and `x/xActions.py` live outside this folder.

Run from **`KK/`**:

```powershell
python FoXYiZ\pyUtils\cleaner.py --apply
python FoXYiZ\pyUtils\reset_demo_data.py
python FoXYiZ\pyUtils\sync_personas.py
python FoXYiZ\pyUtils\zBatchDash.py --name wave1 --since 20260716
```

## Keep (active)

| Script | Why |
|--------|-----|
| `_paths.py` | Shared paths (`FOXYIZ_ROOT`, suites, `z/`) |
| `fOrchestrate.py` | Tag fan-out / parallel batches (Arena + `fEngine2`) |
| `fGUI.py` | Desktop runner GUI |
| `xCustom.py` | End-user custom actions (`xCustom` in yPAD) |
| `zBatchDash.py` | Multi-run HTML batch dashboard |
| `cleaner.py` | Archive dated `z/` noise → `archive/cleanup/` |
| `reset_demo_data.py` | Reset Arena seed projects |
| `sync_personas.py` | Personas: `gen_persona_ypad` + `sync_profiles_from_docs` |
| `gen_persona_ypad.py` | Persona yPAD rows (called by sync) |
| `sync_profiles_from_docs.py` | `profiles.js` from `Docs/test-user-data/` |
| `scaffold_app_ypad.py` | Arena “Add challenge” yPAD scaffold (API) |
| `patch_qoa_web_live_v1.py` | **Live suite** verify gate + locators (idempotent) |
| `gen_journey_ypad.py` | Journey library generator (`--suite qoa_web_live`) |
| `refresh_qoa_web_live.py` | V1 patch + journey regen in one command |
| `fix_y3_journey_locators.py` | Locator append (called by journey gen) |
| `patch_ypad_urls.py` | Post-deploy URL swap for prod smoke |
| `export_demo_bundle.py` | Demo zip for deploy handoff |

## Optional reports

| Script | Output |
|--------|--------|
| `yVisualizer.py` | `y_visualization.html` — yPAD map |
| `zDefects.py` | `zDefectsDashboard.html` — failure rollup |

## Archived one-offs

Applied patches moved to `archive/pyUtils_oneoff/` (heal/fix scripts from past UI migrations).

HTML reports and `z/*_zDash.html` run output stay out of git — see `.gitignore`.
