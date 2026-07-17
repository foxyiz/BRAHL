# qoa_web_live — BRAHL yPAD library

Suite for **current** BRAHL Arena (`/app`) via FoXYiZ.

## Layout

| File | Role |
|------|------|
| `y1Plans.csv` + `y2Actions.csv` | Verify / smoke gate |
| `y1Plans_journey.csv` + `y2Actions_journey.csv` | Journey library (~300) |
| `y3Designs.csv` | Locators (`suite=qoa_web_live`) |
| `qoa_web_live.json` | Full suite (gate + journey) |
| `qoa_web_verify_gate.json` | Gate-only yPAD config |

## Run (canonical fStart)

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py

# CLI Smoke (tags baked in fStart)
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json

# Arena: select qoa_web_live → Run profiles (Smoke / UI / API / …) → Threads → Run
```

One fStart file: `f/fStart/qoa_web_live.json`. Profiles override tags at job time — see [`f/fStart_SCOPE.md`](../../f/fStart_SCOPE.md).

## Refresh journey library

```powershell
python FoXYiZ\pyUtils\refresh_qoa_web_live.py --target 300
```

## Guardrails

- Cite zDash / paths — do not dump full CSVs into AI chat
- Run/Loop = FoXYiZ only (no LLM)
- Prefer Math for tiny loops; this suite for Arena regression

## Latest smoke (2026-07-16)

**24/24** · `FoXYiZ/z/20260716_141654_qoa_web_live/`
