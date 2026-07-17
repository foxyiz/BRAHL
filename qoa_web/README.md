# qoa_web — BRAHL Web App

Local BRAHL web UI over **FoXYiZ**. **Agent handoff:** [MEMORY.md](./MEMORY.md) · **Next:** [../NEXT.md](../NEXT.md) · **Today:** [../todaysummary.md](../todaysummary.md).

```
KK/
  FoXYiZ/     f x y z pyUtils   ← engine (one folder)
  qoa_web/    this web UI + API
  Docs/
  archive/    ← excluded from Cursor context
```

- **Landing:** http://127.0.0.1:8765/welcome  
- **Arena:** http://127.0.0.1:8765/app  
- **Admin:** http://127.0.0.1:8765/admin  
- **Start:** `python qoa_web/run_local.py` from `KK/`

## Quick test

```powershell
python qoa_web/run_local.py
python FoXYiZ\pyUtils\reset_demo_data.py
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
```

fStarts: `f/fStart/{suite}.json` — see [../FoXYiZ/f/fStart_SCOPE.md](../FoXYiZ/f/fStart_SCOPE.md). API runs engine with `cwd=FoXYiZ/`.

## MCP (Cursor agents)

```powershell
python qoa_web/mcp/server.py
```

Tools: `foxyiz_run`, `foxyiz_run_status`, `foxyiz_analyze`, `foxyiz_heal_suggest`, `foxyiz_list_runs`.

## Persona sync / hygiene

```powershell
python FoXYiZ\pyUtils\sync_personas.py
python FoXYiZ\pyUtils\cleaner.py --apply
```

## Context hygiene

Do **not** feed agents `archive/` or `FoXYiZ/z/` (zResults/dashboards). They are ignored via `.cursorignore`.

## Detail docs

| Doc | Purpose |
|-----|---------|
| [qoa_userDoc.md](./qoa_userDoc.md) | User & AI guide |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
| [MEMORY.md](./MEMORY.md) | Agent scope — read first |
| [../Docs/README.md](../Docs/README.md) | Docs hub |
| [../FoXYiZ/README.md](../FoXYiZ/README.md) | Engine folder layout |

**Engine binary:** `FoXYiZ/f/Foxyiz2.exe` is not in git — run `python FoXYiZ/f/fEngine2.py` locally.
