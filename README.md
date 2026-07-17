# FoXYiZ · BRAHL

Local LCNC automation (`f(x,y)=z`) + desktop Arena for **BRAHL** (Build → Run → Analyze → Heal → Loop).

## Layout

```
KK/
  FoXYiZ/    f · x · y · z · pyUtils
  qoa_web/   BRAHL Arena
  Docs/
  NEXT.md · todaysummary.md   ← resume here
  archive/   retired (out of agent context)
```

## Run locally

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
# Welcome: http://127.0.0.1:8765/welcome
# Arena:   http://127.0.0.1:8765/app?demo=1

python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
```

fStarts: **one JSON per suite** under `FoXYiZ/f/fStart/{suite}.json` — see [FoXYiZ/f/fStart_SCOPE.md](FoXYiZ/f/fStart_SCOPE.md).

Run / Loop = FoXYiZ only (never the LLM). Optional AI: `OPENAI_API_KEY` in `FoXYiZ/f/.env`.

## Agents

1. [qoa_web/MEMORY.md](qoa_web/MEMORY.md)  
2. [NEXT.md](NEXT.md) — **todos when you restart**  
3. [todaysummary.md](todaysummary.md)
