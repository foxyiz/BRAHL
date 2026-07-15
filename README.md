# FoXYiZ · BRAHL

Local LCNC automation (`f(x,y)=z`) with a desktop web arena for **BRAHL** (Build → Run → Analyze → Heal → Loop).

## Layout

```
KK/
  FoXYiZ/    f · x · y · z · pyUtils   ← engine (one folder)
  qoa_web/   BRAHL arena (web + API)
  Docs/
  archive/   excluded from Cursor context
```

## Run locally

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
```

- Welcome: http://127.0.0.1:8765/welcome  
- Arena: http://127.0.0.1:8765/app · demo bypass: `/app?demo=1`

## Lean smoke (no OpenAI required)

```powershell
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
```

Run / Loop always use FoXYiZ — never the LLM.

## Optional AI (BYOK)

Set `OPENAI_API_KEY` in `FoXYiZ/f/.env` when ready. See [Docs/BRAHL_DESKTOP_BYOK.md](Docs/BRAHL_DESKTOP_BYOK.md).

## Agents / scope

Start at [qoa_web/MEMORY.md](qoa_web/MEMORY.md). Engine: [FoXYiZ/README.md](FoXYiZ/README.md).  
**Today's changes:** [todaysummary.md](todaysummary.md) · Docs hub: [Docs/README.md](Docs/README.md).

Do not index `archive/` or `FoXYiZ/z/` (zResults) into agent context.
