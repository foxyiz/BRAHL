# qoa_web_live — BRAHL yPAD library

Suite for testing **current** BRAHL Arena (`/app`) with FoXYiZ.

## Versions

| Version | What | Status |
|---------|------|--------|
| **V1 (now)** | Verify gate + AI .md / Build doc chips / Heal Apply CTA · suite `qoa_web_live` · version **1.4.0-v1** | Active |
| **V2 (later)** | Re-BRAHL Journey library (~800) via `python pyUtils/gen_journey_ypad.py --target 800` pointed at this suite | Not run yet |

Yes: **V1 gate first, re-BRAHL Journey later** is the right cadence.

## Files

| File | Role |
|------|------|
| `y1Plans.csv` + `y2Actions.csv` | Verify gate (~58 Run=Y) |
| `y1Plans_journey.csv` + `y2Actions_journey.csv` | Overnight Journey (legacy 800; refresh in V2) |
| `y3Designs.csv` | Locators / URLs (persona D1–D9) |
| `qoa_web_live.json` | Full suite (gate + journey) |
| `qoa_web_verify_gate.json` | Gate only |

## Run

```powershell
# From KK/ — V1 verify gate (headless smoke)
cd FoXYiZ
python f\fEngine2.py --config f\fStart_qoa_web_live_smoke_headless.json

# V1.4 AI / Build-doc slice
python f\fEngine2.py --config f\fStart_qoa_web_live_ai_smoke.json

# Re-apply V1 patches after UI edits (idempotent-ish)
python pyUtils\patch_qoa_web_live_v1.py
```

App must be up: `python qoa_web/run_local.py` → http://127.0.0.1:8765/

Persona deep links use `suite=qoa_web_live`.

## Guardrails

- Do not dump full CSVs into AI chat — cite paths / zDash only.
- Run/Loop stay FoXYiZ-only (no LLM).
- Prefer Math for tiny loops; use this suite for Arena regression.
