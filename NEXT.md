# Next — pick up here

After a break: hard-refresh Arena (`Ctrl+F5`), restart `run_local` if API changed.

## Resume checklist

1. **Start Arena** — `python qoa_web/run_local.py` → `/app?demo=1` · Ctrl+F5
2. **Build** — one-line blurb · **Edit** top-right · Gate/Journey source chips · **Snapshot** before big rebuilds
3. **Run** — one fStart + Edit · profile chips · Threads · one **Run** (parallel when Threads>1 + 2+ profiles)
4. **BRAHL** — Reports first · Automation | Human verified · embedded zDash
5. **QA Hunter** — one **+ Add evidence** menu · project evidence library
6. **Loop** — provenance strip · Schedules (beta) local/cloud with cost hint
7. **Commit** when happy — no `FoXYiZ/z/` or secrets

## Known follow-ups

| Priority | Item |
|----------|------|
| P1 | Optional: retag yPAD to only Smoke/UI/API/… (map still works) |
| P1 | `qoa_web_live` journey has **0 API-tagged** plans — add coverage or remap |
| P2 | Deploy / EC2 / Stripe / OAuth ([todo.md](todo.md)) |
| P2 | Cloud multi-user sync for schedules/evidence (schema is ready) |

## Latest smoke

**27/27** · `FoXYiZ/z/20260716_223731_qoa_web_live/` · video-review UI (Add evidence, BRAHL tabs, Schedules, Threads, Heal AI)

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
python -m pytest qoa_web/api/test_ypad_source.py qoa_web/api/test_ypad_versions.py qoa_web/api/test_evidence_schedules.py -v
```
