# u/ — Python utilities (PyUtils)

**Formula:** `f(x, y) = z` — **`f/`** engine and **`x/`** actions are **not** in this folder.

All helper scripts live here so humans and agents touch one place. Run from **`KK/`**:

```powershell
python u/cleaner.py              # dry-run: what would be archived
python u/cleaner.py --apply      # move ephemeral z/ output to archive/cleanup/
python u/sync_personas.py        # regen yPAD + profiles.js from Docs/test-user-data/
python u/gen_persona_ypad.py     # y/qoa_web y1/y2/y3 CSVs only
python u/gen_journey_ypad.py --target 800   # journey regression library
python u/sync_profiles_from_docs.py
python u/yVisualizer.py          # u/y_visualization.html
python u/zDefects.py             # u/zDefectsDashboard.html
python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log  # z/zDash_batch_<name>.html
python u/export_demo_bundle.py   # slim VPS deploy bundle
python u/patch_ypad_urls.py      # APP_BASE_URL → yPAD URLs (before prod verify)
python u/reset_demo_data.py     # reset projects.json before verify (join state)
```

HTML reports from **`u/`** scripts write to **`u/`** (same folder as the Python utilities). FoXYiZ verify dashboards (`*_zDash.html`) still land under **`z/<run>/`** from `f/fEngine2.py`.

## Scripts

| Script | Purpose |
|--------|---------|
| **cleaner.py** | Archive brahl reports, dated `z/` runs, probes → `archive/cleanup/<ts>/`. Delete `archive/cleanup/` anytime. |
| **sync_personas.py** | Runs `gen_persona_ypad` + `sync_profiles_from_docs` |
| **gen_persona_ypad.py** | Persona columns D1–D9 → `y/qoa_web/*.csv` |
| **gen_journey_ypad.py** | ~600–1000 journey plans → `y1Plans_journey.csv` (tag Journey) |
| **fix_y3_journey_locators.py** | Repair/append journey UI locators in y3Designs |
| **sync_profiles_from_docs.py** | `Docs/test-user-data/` → `qoa_web/web/profiles.js` |
| **yVisualizer.py** | yPAD workflow HTML graph → `u/y_visualization.html` |
| **zDefects.py** | Aggregate `*_zResults.csv` failures → `u/zDefectsDashboard.html` |
| **zBatchDash.py** | Aggregate parallel batch runs → `z/zDash_batch_<name>.html` (time comparison + per-job links) |
| **export_demo_bundle.py** | Zip slim deploy bundle for VPS (`archive/demo-bundle/`) |
| **reset_demo_data.py** | Copy `projects.seed.json` → `projects.json` before verify |

## After a work session

See [Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) for the full checklist (~30 min).

```powershell
python u/cleaner.py --apply
```

Optional monthly: `python u/cleaner.py --apply --purge-archive`

## Do not put here

- `f/fEngine2.py` — FoXYiZ engine
- `x/xActions.py`, `x/xCustom.py` — action handlers
- `qoa_web/run_local.py`, `qoa_web/api/*` — web app (not utilities)

Old paths (`y/yVisualizer.py`, `z/zDefects.py`, etc.) are thin wrappers that delegate to `u/`.
