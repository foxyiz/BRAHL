One-off Playwright probe outputs, cleaner archives, and optional demo export bundles.

| Folder | Contents |
|--------|----------|
| `probes/` | Legacy probe JSON/scripts (out of qoa_web v1 scope) |
| `cleanup/<timestamp>/` | Moved by `python u/cleaner.py --apply` — **safe to delete entire `cleanup/` folder** |
| `demo-bundle/` | Output of `python u/export_demo_bundle.py` — keep latest only; delete old snapshots |

Run cleaner after FoXYiZ sessions to keep `z/` and repo context small.
