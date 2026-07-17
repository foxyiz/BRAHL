# qoa_web workspace data

## user_ai_docs/

Optional markdown for the arena `.md` drawer. Caps in `api/ai_docs.py`.

## projects.json

Runtime metadata: chat, budget, HITL, BRAHL links. Reset: `python FoXYiZ/pyUtils/reset_demo_data.py`.

## Suites ↔ fStart

| Suite | yPAD | fStart (canonical) |
|-------|------|--------------------|
| Math | `FoXYiZ/y/Math/` | `f/fStart/Math.json` |
| nalanda_app | `FoXYiZ/y/nalanda_app/` | `f/fStart/nalanda_app.json` |
| qoa_web | `FoXYiZ/y/qoa_web/` | `f/fStart/qoa_web.json` |
| qoa_web_live | `FoXYiZ/y/qoa_web_live/` | `f/fStart/qoa_web_live.json` |

Old per-tag JSONs: `FoXYiZ/f/fStart/archive/`. See [`f/fStart_SCOPE.md`](../../FoXYiZ/f/fStart_SCOPE.md).

## Personas

| Output | Source | Regenerate |
|--------|--------|------------|
| `qoa_web/web/profiles.js` | `Docs/test-user-data/` | `python FoXYiZ/pyUtils/sync_personas.py` |
