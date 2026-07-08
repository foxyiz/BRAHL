# Session maintenance (~every 30 minutes or end of work)

Keep the repo **small**, docs **accurate**, and AI context **easy to reload**.

Run from **`KK/`**.

---

## pyUtils test run log

| When | Script | Command | Output |
|------|--------|---------|--------|
| 2026-07-07 | **cleaner.py** | `python pyUtils/cleaner.py` (default dry-run) | `pyUtils/_run_cleaner.log` — would archive **32** items under `z/` (dated runs + brahl reports). No files moved. |
| 2026-07-07 | **yVisualizer.py** | `python pyUtils/yVisualizer.py` (default — all workflows in `y/`) | `pyUtils/y_visualization.html` + `pyUtils/_run_yVisualizer.log` |
| 2026-07-07 | **zDefects.py** | `python pyUtils/zDefects.py` (default) | `pyUtils/zDefectsDashboard.html` — **249** defects aggregated from `z/**/*_zResults.csv` |
| 2026-07-07 | **zBatchDash.py** | `python pyUtils/zBatchDash.py --name pyutils_test --since 20260706_214 --suite qoa_web_verify_gate` | `pyUtils/zDash_batch_pyutils_test.html` (copy of `z/zDash_batch_pyutils_test.html`) — **4** jobs, **60/88** plans passed |

Utilities folder: **`pyUtils/`** (formerly `u/`). HTML reports from viz/defects tools write to **`pyUtils/`**.

---

## Quick checklist

| Step | Command / action |
|------|------------------|
| 1. Archive noise | `python pyUtils/cleaner.py` (dry-run) then `python pyUtils/cleaner.py --apply` |
| 2. Optional viz archive | `python pyUtils/cleaner.py --apply --viz` — moves `pyUtils/y_visualization.html`, `pyUtils/zDefectsDashboard.html` to `archive/cleanup/` |
| 3. Regenerate reports (if needed) | `python pyUtils/yVisualizer.py` · `python pyUtils/zDefects.py` |
| 4. Update doc dates | `Summary.md`, `Docs/README.md` footer — **Last updated** |
| 5. Sync verify count | Count `Run=Y` in `y/qoa_web/y1Plans.csv` → update `qoa_web/MEMORY.md`, `qoa_web/README.md`, `Docs/README.md` |
| 6. Persona drift | If you edited `Docs/test-user-data/` → `python pyUtils/sync_personas.py` |

Monthly (optional): `python pyUtils/cleaner.py --apply --purge-archive` — deletes `archive/cleanup/` older than 30 days.

---

## What `cleaner.py` moves

Into `archive/cleanup/<timestamp>/`:

- Dated folders under `z/` (verify runs, dashboards, `_errors.csv`)
- Root-level `z/brahl_report_*.md`
- Root probe leftovers (`*_probe.json`, `*_probe.py`)
- With `--viz`: utility HTML in `pyUtils/` (regenerate anytime)

**Keeps in place:** `z/zDash_template.html`, thin wrappers `z/zDefects.py`, `y/yVisualizer.py`.

**Safe to delete:** entire `archive/cleanup/` folder anytime.

---

## Doc files to keep aligned

When product or verify scope changes, update **all** that apply:

| Change | Update |
|--------|--------|
| New plans / Run flags | `y/qoa_web/y1Plans.csv`, verify count in MEMORY, README, Docs/README |
| Avatar / copy | `qoa_web/web/`, `qoa_userDoc.md`, signin/about if needed |
| BRAHL protocol | `Docs/BRAHL.md`, slim `Docs/BRAHL_PROMPT.md` |
| yPAD rules | `Docs/FoXYiZ.md` |
| Agent boundaries | `Docs/rules.md`, `qoa_web/MEMORY.md`, `.cursorignore` |
| Deploy | `qoa_web/DEPLOY.md` |

Do **not** edit plan `.md` files in `y/` unless explicitly requested — yPAD is CSV-first.

---

## Verify health (qoa_web)

```powershell
python qoa_web/run_local.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json
```

**BRAHL loop** (after failures): see [BRAHL.md](./BRAHL.md) — Loop 1 full → Loops 2–3 failures-only → restore all `Run=Y` → Verify → report.

Current target: **49/49** (`fStart_qoa_web_verify.json`, tag **Verify**, `Run=Y` only).

---

## Token efficiency for Cursor

`.cursorignore` excludes inactive suites and old `z/` runs. **Do not** add `Docs/` or `Summary.md` to ignore — they are the handoff layer.

If context feels stale after a long session, start a **new chat** and @ `Docs/README.md` + `qoa_web/MEMORY.md`.
