# qoa_web — BRAHL Web App v1.3

Local BRAHL web UI + FoXYiZ API. **Agent handoff:** [MEMORY.md](./MEMORY.md) · Team index: [Summary.md](../Summary.md).

- **Landing:** http://127.0.0.1:8765/welcome  
- **Arena:** http://127.0.0.1:8765/app  
- **Start:** `python qoa_web/run_local.py` from `KK/`

## Quick test

```powershell
python qoa_web/run_local.py
python u/reset_demo_data.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json   # 49 plans, server required
```

**Latest verify:** **49/49** — tag **Verify**, `Run=Y` in `y1Plans.csv`

## MCP (Cursor agents)

```powershell
python qoa_web/mcp/server.py
```

Tools: `foxyiz_run`, `foxyiz_run_status`, `foxyiz_analyze`, `foxyiz_heal_suggest`, `foxyiz_list_runs`.

## Persona sync (after editing test users)

```powershell
python u/sync_personas.py
```

Source of truth: `Docs/test-user-data/*.json`.

## Context hygiene

```powershell
python u/cleaner.py --apply
```

Utilities: [u/README.md](../u/README.md) — **not** `f/` engine or `x/` actions.

## Detail docs

| Doc | Purpose |
|-----|---------|
| [qoa_userDoc.md](./qoa_userDoc.md) | **User & AI guide** — invite GTM, personas, phases |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
| [MEMORY.md](./MEMORY.md) | Agent scope — read first |
| [../Docs/README.md](../Docs/README.md) | Docs hub — new machine / export |

**Engine binary:** `f/Foxyiz2.exe` is not in git — run `python f/fEngine2.py` locally or rebuild per [Summary.md](../Summary.md#build-exe).
