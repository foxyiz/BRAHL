# Next — pick up here

After a break: hard-refresh Arena (`Ctrl+F5`), restart `run_local` if API changed.  
Vocabulary: [Docs/terminology.md](Docs/terminology.md).

## Resume checklist

1. **Start Arena** — `python qoa_web/run_local.py` → `/app?demo=1` · Ctrl+F5
2. **Build** — one-line blurb · **Edit** · Snapshot before big rebuilds
3. **Run** — suite fStart · profile/tags · Threads
4. **BRAHL** — Reports · Automation | Human · embedded zDash · Conclusion GO/NO-GO
5. **Cleanup** — `python FoXYiZ\pyUtils\cleaner.py --apply`
6. **Commit** when asked — no `FoXYiZ/z/` or secrets

## Known follow-ups

| Priority | Item |
|----------|------|
| P1 | ThoughtStream: expand Manual→auto when mic/OAuth/OTP fixtures exist; grow D4+ personas/hosts |
| P1 | Optional: retag suites to only Smoke/UI/API/… profiles |
| P2 | Deploy / EC2 / Stripe / OAuth ([todo.md](todo.md)) |
| P2 | Cloud multi-user sync for schedules/evidence |

## Latest verified

| Suite | Result | Notes |
|-------|--------|-------|
| **thoughtstream** deep | **49/49 GO** | `thoughtstream_deep.json` · Arena `0935e530a120` · snapshot v3-deep-regression |
| thoughtstream Conclusion | 2/2 | Smoke + Deep BRAHL gates |
| a77 | Smoke/UI green (prior) | Guest-arch v4 |
| qoa_web_live | Smoke 27/27 (prior) | Arena self-test |

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream_deep.json
python FoXYiZ\pyUtils\cleaner.py --apply
```
