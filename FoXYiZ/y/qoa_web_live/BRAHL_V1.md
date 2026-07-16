# qoa_web_live — BRAHL yPAD library

Suite for testing **current** BRAHL Arena (`/app`) with FoXYiZ.

## Versions

| Version | What | Status |
|---------|------|--------|
| **V1** | Verify gate · `qoa_web_verify_gate.json` · **69** plans (**62** Run=Y) | Active |
| **V2** | Journey library · regen via `refresh_qoa_web_live.py` · **~300** focused plans | Active |

## Refresh (V1 + V2)

```powershell
cd c:\006\FXYZ\KK
python FoXYiZ\pyUtils\refresh_qoa_web_live.py --target 300
```

## Files

| File | Role |
|------|------|
| `y1Plans.csv` + `y2Actions.csv` | Verify gate |
| `y1Plans_journey.csv` + `y2Actions_journey.csv` | Journey (tag `Journey;qoa_web_live;…`) |
| `y3Designs.csv` | Locators / URLs (`suite=qoa_web_live`) |
| `qoa_web_live.json` | Full suite (gate + journey) |
| `qoa_web_verify_gate.json` | Gate only |

## Run

```powershell
# App up first
python qoa_web/run_local.py

# V1 verify smoke (gate only)
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live_smoke_headless.json

# V2 journey slices (after refresh)
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live_journey_nav.json
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live_journey_brahl.json
```

## Guardrails

- Do not dump full CSVs into AI chat — cite paths / zDash only.
- Run/Loop stay FoXYiZ-only (no LLM).
- Prefer Math for tiny loops; use this suite for Arena regression.
