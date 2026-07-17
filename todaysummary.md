# Today's summary — 2026-07-16 (continued)

Spelling: **BRAHL** · **FoXYiZ**.

## BRAHL video review — shipped

Plan (do not edit): desktop review → Build/Run/Hunter/BRAHL/Loop improvements.

### Phase 0 — Data safety
- Multi-file yPAD writes require explicit `source` (gate vs journey)
- ENV/credential D* values redacted in Arena
- Contract tests: `qoa_web/api/test_ypad_source.py`

### Phase 1 — Build / yPAD
- One-line Build blurb; removed Improve yPADs / Test coverage dupes
- Full-width doc modals; Edit top-right; insights-first + Show table / pagination
- Gate/Journey source chips; immutable snapshots under `y/<suite>/versions/`
- Diff / merge missing / restore · `CreatedBy`/`CreatedAt` on scaffolded plans
- Tests: `qoa_web/api/test_ypad_versions.py`

### Phase 2 — QA Hunter evidence
- One **+ Add evidence** menu (screen/audio/image/file/URL/note)
- Project `evidence_library` + list/add/link APIs; reports accept `evidence_ids`

### Phase 3 — Run + BRAHL
- Removed **New** / **Run parallel**; Threads + profiles drive parallel
- Project-switch request sequencing + loading
- Batch registers all `run_dirs`; BRAHL Reports first with Automation | Human tabs + embedded zDash

### Phase 4 — Loop / schedules
- Explicit Analyze / Heal / Loop copy + Loop provenance
- Local schedules (`qoa_web/data/schedules.json`) hourly/daily · local/cloud cost estimate
- Poller reuses `start_run` (no AI in scheduled Verify)

### Verification
- API: `test_ypad_source` + `test_ypad_versions` + `test_evidence_schedules` (**24 passed**)
- Smoke yPAD updated for new headings / Threads / Add evidence / BRAHL tabs / Schedules
- **qoa_web_live Smoke 27/27** · `z/20260716_223731_qoa_web_live/`
- Nalanda Smoke+UI `thread_count=2` → parallel job + `zDash_batch_*` + `/brahl/reports/batch` registration
- Math engine still runnable (pre-existing expected-value mismatches on 2 plans)

## Earlier this day
- Run profiles Smoke=gate / UI=journey · Heal AI · z/ cleanup → `C:\006\FXYZ\archive\cleanup\`

## Resume

[`NEXT.md`](NEXT.md)
