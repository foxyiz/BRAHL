# qoa_web v1.0 — Local Launch Guide

Run the full BRAHL desktop stack on your machine before sharing with the team.

## Prerequisites

- Python 3.10+ with `pip install -r qoa_web/api/requirements.txt`
- Edge or Chrome (FoXYiZ default: Edge)
- FoXYiZ deps: `pip install -r f/requirements.txt`

## Start (2 terminals)

**Terminal 1 — Web app**

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
```

Open http://127.0.0.1:8765 · hard-refresh after code changes.

**Terminal 2 — Full verify (optional gate before demo)**

```powershell
cd c:\006\FXYZ\KK
python f\fEngine2.py --config f\fStart_qoa_web_verify.json
```

Expect **60/60** plans · dashboard in `z/<timestamp>_qoa_web/`.

## Avatar checklist

| Feature | Client (C) | HITL (H) |
|---------|--------------|----------|
| Avatar gate | ✓ | ✓ |
| Project picker (top bar + Build) | ✓ | ✓ |
| Build workspace | AI chat, checklist, budget | Grid, join, deliverables |
| Run / Analyze / Heal / Loop / BRAHL | ✓ scoped | ✓ scoped |
| Phase progress bar | ✓ | ✓ |
| Shrink / restore yPAD | ✓ | ✓ |
| BRAHL reports + model chat | ✓ | ✓ |

Test project: **qoa_web Local** (`d21afcefc002`).

## MCP for Cursor agents

```powershell
python qoa_web/mcp/server.py
```

Requires qoa_web server running on :8765.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8765 in use | Stop old `run_local.py` process, restart |
| Stale UI | Hard-refresh browser (Ctrl+Shift+R) |
| Verify failures | Restart server; check `z/_errors.csv` |
| Avatar gate in tests | Use `/?reset=1` (see `fresh_url` in yPAD) |

## Docs

- [CHANGELOG.md](./CHANGELOG.md) — v1.0 features
- [Summary.md](../Summary.md) — team handoff index
- [AVATARS_AND_BUILD.md](./AVATARS_AND_BUILD.md) — roles & APIs
