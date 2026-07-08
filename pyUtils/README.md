# pyUtils — Python utilities (PyUtils)

**Formula:** `f(x, y) = z` — **`f/`** engine and **`x/`** actions are **not** in this folder.

All helper scripts live here so humans and agents touch one place. Run from **`KK/`**:

```powershell
python pyUtils/cleaner.py              # dry-run: what would be archived
python pyUtils/cleaner.py --apply      # move ephemeral z/ output to archive/cleanup/
python pyUtils/sync_personas.py        # regen yPAD + profiles.js from Docs/test-user-data/
python pyUtils/gen_persona_ypad.py     # y/qoa_web y1/y2/y3 CSVs only
python pyUtils/gen_journey_ypad.py --target 800   # journey regression library
python pyUtils/sync_profiles_from_docs.py
python pyUtils/yVisualizer.py          # pyUtils/y_visualization.html
python pyUtils/zDefects.py             # pyUtils/zDefectsDashboard.html
python pyUtils/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log  # z/zDash_batch_<name>.html (copy to pyUtils if desired)
python pyUtils/export_demo_bundle.py   # slim VPS deploy bundle
python pyUtils/patch_ypad_urls.py      # APP_BASE_URL → yPAD URLs (before prod verify)
python pyUtils/reset_demo_data.py     # reset projects.json before verify (join state)
```

HTML reports from **`pyUtils/`** scripts write to **`pyUtils/`** (same folder as the Python utilities). FoXYiZ verify dashboards (`*_zDash.html`) still land under **`z/<run>/`** from `f/fEngine2.py`; copy batch dashboards into `pyUtils/` when you want them alongside the other utility HTML.

## Test run (2026-07-07)

| Script | Default command | Output in `pyUtils/` |
|--------|-----------------|----------------------|
| cleaner.py | `python pyUtils/cleaner.py` | `_run_cleaner.log` (dry-run, 32 items would archive) |
| yVisualizer.py | `python pyUtils/yVisualizer.py` | `y_visualization.html` |
| zDefects.py | `python pyUtils/zDefects.py` | `zDefectsDashboard.html` (249 defects) |
| zBatchDash.py | requires `--name` + `--since`/`--runs`/`--logs` | `zDash_batch_pyutils_test.html` (4 verify-gate jobs, 60/88 passed) |

See [Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) for the full session checklist.

## Scripts

| Script | Purpose |
|--------|---------|
| **cleaner.py** | Archive brahl reports, dated `z/` runs, probes → `archive/cleanup/<ts>/`. Delete `archive/cleanup/` anytime. |
| **sync_personas.py** | Runs `gen_persona_ypad` + `sync_profiles_from_docs` |
| **gen_persona_ypad.py** | Persona columns D1–D9 → `y/qoa_web/*.csv` |
| **gen_journey_ypad.py** | ~600–1000 journey plans → `y1Plans_journey.csv` (tag Journey) |
| **fix_y3_journey_locators.py** | Repair/append journey UI locators in y3Designs |
| **sync_profiles_from_docs.py** | `Docs/test-user-data/` → `qoa_web/web/profiles.js` |
| **yVisualizer.py** | yPAD workflow HTML graph → `pyUtils/y_visualization.html` |
| **zDefects.py** | Aggregate `*_zResults.csv` failures → `pyUtils/zDefectsDashboard.html` |
| **zBatchDash.py** | Aggregate parallel batch runs → `z/zDash_batch_<name>.html` (copy to `pyUtils/` if desired) |
| **export_demo_bundle.py** | Zip slim deploy bundle for VPS (`archive/demo-bundle/`) |
| **reset_demo_data.py** | Copy `projects.seed.json` → `projects.json` before verify |

## After a work session

See [Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) for the full checklist (~30 min).

```powershell
python pyUtils/cleaner.py --apply
```

Optional monthly: `python pyUtils/cleaner.py --apply --purge-archive`

## Do not put here

- `f/fEngine2.py` — FoXYiZ engine
- `x/xActions.py`, `x/xCustom.py` — action handlers
- `qoa_web/run_local.py`, `qoa_web/api/*` — web app (not utilities)

Old paths (`y/yVisualizer.py`, `z/zDefects.py`, etc.) are thin wrappers that delegate to `pyUtils/`.
