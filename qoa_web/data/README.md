# qoa_web workspace data

## user_ai_docs/

Optional end-user markdown for the arena `.md` drawer (`manifest.json` + `*.md`). Caps in `api/ai_docs.py`.

## projects.json

Runtime workspace metadata: chat, budget, HITL, BRAHL links.

- **API:** `qoa_web/api/projects.py`
- **Reset:** `python FoXYiZ/pyUtils/reset_demo_data.py`

## invites.json · nalanda.json · presence.json

Invite GTM, Nalanda community, Admin presence heartbeat.

## Suites

| Suite | Path | Smoke |
|-------|------|-------|
| Math | `FoXYiZ/y/Math/` | `f/fStart_Math.json` |
| nalanda_app | `FoXYiZ/y/nalanda_app/` | `f/fStart_nalanda_app_smoke.json` |
| qoa_web_live | `FoXYiZ/y/qoa_web_live/` | gate configs under `FoXYiZ/f/` |

## Personas

| Output | Source | Regenerate |
|--------|--------|------------|
| `qoa_web/web/profiles.js` | `Docs/test-user-data/` | `python FoXYiZ/pyUtils/sync_personas.py` |

Edit persona JSON under `Docs/test-user-data/`, then sync. See [Docs/test-user-data/README.md](../../Docs/test-user-data/README.md).
