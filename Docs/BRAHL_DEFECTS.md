# BRAHL / qoa_new — Defect closure log

Sources: [Issues.docx](./Issues.docx) (BRAHL-001–004) · [Issues noticed on qoa_new.docx](./Issues%20noticed%20on%20qoa_new.docx) (+ PDF).

Fixed 2026-07-07 in `qoa_web/api/runner.py`, `projects.py`, `main.py`, `web/app.js`, `web/index.html`, `web/styles.css`.

| ID | Issue | Root cause | Fix | Status |
|----|-------|-----------|-----|--------|
| BRAHL-001 | Inconsistent pass counts (2/33/71) | `list_z_runs()` counted CSV action rows; `analyze_run()` counted plans | Shared `plan_stats_from_zresults()`; all surfaces use plan-level counts | Fixed |
| BRAHL-002 | View zDash → File not found | UI hardcoded `qoa_web_zDash.html` | `zDashHref()` resolves real `*_zDash.html` from API `dashboard` | Fixed |
| BRAHL-003 | Loop recovery not visible | `cycle_history` had no pass/fail snapshot | `append_cycle_event()` attaches `stats`; cycle history shows counts + Recovered badge; `## Recovery trace` in report | Fixed |
| BRAHL-004 | Run vs Analyze stats mismatch | Same as 001 (row vs plan) | Unified via `plan_stats_from_zresults()` + `/api/runs/{run}/stats` | Fixed |
| QOA-RUN-001 | Hardcoded zDash routing | = BRAHL-002 | Same | Fixed |
| QOA-RUN-002 | 16 fails vs 15 plans | = BRAHL-001/004 | Plan-level counts; `fails ≤ total_plans` (unit test) | Fixed |
| QOA-PRO-001 | P1 blocked from QA Hunter/Nalanda | By design — P1 is `allowed_avatars: ["client"]` | UX fix: restricted avatars disabled with tooltip (not silent) | Fixed (UX) |
| QOA-BLD-001 | Cost meter shows on some projects only | Teaser hidden when no budget | Empty-state hint "Set a budget on the $ tab…" | Fixed |
| QOA-BLD-002 | `.env` example unclear | No guidance on where secrets go | ENV panel relabeled "Reference only — copy to `f/.env` on server" | Fixed |
| QOA-BLD-003 | Invite QA Hunter no-op | `openInviteHitlModal()` returned silently when no project | Status message + button disabled without a project | Fixed |
| QOA-ARC-001 | Build vs BRAHL "B=Build" confusion | Copy only | Phase hints clarify Build=product, BRAHL=launch report | Fixed (copy) |
| QOA-UX-002 | AI `.md` viewer horizontal overflow | Missing wrap constraints | `.ai-docs-doc-body`: `overflow-wrap: anywhere; max-width: 100%` | Fixed |
| QOA-UX-001 | Cluttered UI | Broad | Minimal pass only (empty states, copy); large redesign deferred | Partial |
| QOA-TECH-001 | Heavy localStorage | Architecture | Roadmap only — no DB migration in this pass | Deferred |

## Verification checklist

1. `python qoa_web/run_local.py`
2. P1 profile: QA Hunter/Nalanda avatars show disabled with tooltip; Creator works.
3. Build: Invite QA Hunter opens modal with a project; disabled + status without one.
4. Run: View zDash opens the correct `*_verify_gate_zDash.html`.
5. Analyze / BRAHL / Run list: same `passes/total_plans` everywhere.
6. Loop: Shrink → Loop 2 → Verify; cycle history shows counts + Recovered badge.
7. AI docs modal: long lines wrap, no off-screen scroll.

Unit test: `python -m pytest qoa_web/api/test_runner_stats.py -q` (asserts `fails ≤ total_plans`).
