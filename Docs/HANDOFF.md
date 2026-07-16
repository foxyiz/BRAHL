# Handoff — current KK

**Read first:** [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) · **Today's log:** [../todaysummary.md](../todaysummary.md) · **Backlog:** [../todo.md](../todo.md)

## Product

| Piece | Role |
|-------|------|
| `FoXYiZ/` | Engine `f(x,y)=z` — f · x · y · z · pyUtils |
| `qoa_web/` | BRAHL Arena UI + API · http://127.0.0.1:8765 |
| `Docs/` | Slim reference (this hub's README) |
| `archive/` | Retired noise — never load into agent context |

Naming: always **BRAHL** · **FoXYiZ**.

## Bootstrap (new machine)

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
# optional AI: set OPENAI_API_KEY in FoXYiZ/f/.env
python qoa_web/run_local.py
# Arena: /app?demo=1
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
```

## AI bootstrap (@-mention only)

1. `qoa_web/MEMORY.md`
2. `todaysummary.md` (latest session)
3. `Docs/BRAHL_PROMPT.md` / `Docs/AI_GUARDRAILS.md` for in-app AI behavior

Deep dives: `Docs/BRAHL.md`, `Docs/FoXYiZ.md`, `FoXYiZ/FoXYiZ_Readme.md`.

## Docs that stay in KK/Docs

See [README.md](./README.md). Retired → `archive/docs-retired-20260714/`.
