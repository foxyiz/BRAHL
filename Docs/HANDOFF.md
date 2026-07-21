# Handoff — current KK

**Read first:** [terminology.md](./terminology.md) · [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) · **Today:** [../todaysummary.md](../todaysummary.md) · **Next:** [../NEXT.md](../NEXT.md)

## Product

| Piece | Role |
|-------|------|
| `FoXYiZ/` | Engine `f(x,y)=z` — f · x · y · z · pyUtils |
| `qoa_web/` | BRAHL Arena · http://127.0.0.1:8765 |
| `Docs/` | Slim reference (start: terminology → this file) |
| `archive/` | Retired / cleanup — never load into agent context |

Naming: **BRAHL** · **FoXYiZ**. Verb: **brawled** = completed a BRAHL cycle. See [terminology.md](./terminology.md).

## Bootstrap

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
# optional AI: OPENAI_API_KEY in FoXYiZ/f/.env
python qoa_web/run_local.py
# Arena: /app?demo=1
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream.json
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream_deep.json
```

fStarts: **one file per suite** under `FoXYiZ/f/fStart/{suite}.json`. Deep lanes may add `{suite}_deep.json` for tags only. See [../FoXYiZ/f/fStart_SCOPE.md](../FoXYiZ/f/fStart_SCOPE.md).

## Current precision — ThoughtStream (2026-07-20)

| Item | Value |
|------|-------|
| App | https://jusdone.base44.app/ (UI brand ThoughtCapture) |
| Suite | `FoXYiZ/y/thoughtstream/` |
| yPAD | ~92 plans · ~77 Run=Y · ~15 Manual |
| Deep verify | **49/49** · BRAHL **GO** · Arena `0935e530a120` |
| Snapshot | `y/thoughtstream/versions/*_v3-deep-regression` |
| Personas | D1 Guest Capturer · D2 Guest Researcher · D3 Embed Integrator |

Heal against **live UI text** (e.g. idea detail uses `Add file` / `KEY POINTS`, not obsolete labels). Do not re-click “Try samples” when the guest browser is already seeded.

## AI bootstrap (@-mention)

1. `Docs/terminology.md`
2. `qoa_web/MEMORY.md`
3. `NEXT.md` / `todaysummary.md`
4. `Docs/BRAHL_PROMPT.md` / `Docs/AI_GUARDRAILS.md` if touching AI

Deep: `Docs/BRAHL.md`, `Docs/FoXYiZ.md`.

## Cleanup

```powershell
python FoXYiZ\pyUtils\cleaner.py --apply
python FoXYiZ\pyUtils\cleaner.py --apply --ypad-versions          # keep 2 newest version folders/suite
python FoXYiZ\pyUtils\cleaner.py --apply --runtime-scratch
```

- **z/** — keeps latest BRAHL-reported run per suite  
- **y/…/versions/** — historical CSV snapshots; older ones archive out of AI context  
- Live yPAD (`y1`/`y2`/`y3`) always stays in the suite folder

## yPAD version habit

Before a major expansion: Arena **Snapshot** (or copy CSVs into `y/<suite>/versions/<ts>_<label>/`).  
ThoughtStream already has v1→v3 history; cleanup keeps the newest two in-tree.
