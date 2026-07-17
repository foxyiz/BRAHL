# Handoff — current KK

**Read first:** [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) · **Today:** [../todaysummary.md](../todaysummary.md) · **Next:** [../NEXT.md](../NEXT.md)

## Product

| Piece | Role |
|-------|------|
| `FoXYiZ/` | Engine `f(x,y)=z` — f · x · y · z · pyUtils |
| `qoa_web/` | BRAHL Arena · http://127.0.0.1:8765 |
| `Docs/` | Slim reference |
| `archive/` | Retired — never load into agent context |

Naming: **BRAHL** · **FoXYiZ**.

## Bootstrap

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
# optional AI: OPENAI_API_KEY in FoXYiZ/f/.env
python qoa_web/run_local.py
# Arena: /app?demo=1
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
```

fStarts: **one file per suite** under `FoXYiZ/f/fStart/{suite}.json`. See [../FoXYiZ/f/fStart_SCOPE.md](../FoXYiZ/f/fStart_SCOPE.md).

## AI bootstrap (@-mention)

1. `qoa_web/MEMORY.md`
2. `NEXT.md` / `todaysummary.md`
3. `Docs/BRAHL_PROMPT.md` / `Docs/AI_GUARDRAILS.md` if touching AI

Deep: `Docs/BRAHL.md`, `FoXYiZ/FoXYiZ_Readme.md`.
