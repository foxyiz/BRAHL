# Agent & team rules (KK)

Standing conventions for humans and AI working in this workspace.

Related: [terminology.md](./terminology.md) · [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) · [AI_GUARDRAILS.md](./AI_GUARDRAILS.md) · [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md)

## Vocabulary first

Always spell **BRAHL** and **FoXYiZ**. Use **brawled** for a completed BRAHL cycle. Full glossary: [terminology.md](./terminology.md).

## Explore apps with Playwright MCP

Do **not** add one-off Python scrapers. Use Playwright (`browser_navigate`, `browser_snapshot`, …), then edit **yPAD** CSVs.

## Default edit scope

| Touch | Avoid unless asked |
|-------|--------------------|
| `qoa_web/web/*`, `qoa_web/api/*` | `FoXYiZ/f/fEngine2.py`, `FoXYiZ/x/xActions.py` |
| `FoXYiZ/y/<suite>/*.csv`, `*.json` | Dumping `FoXYiZ/z/**` into chat |
| `FoXYiZ/f/fStart/{suite}.json` | `archive/**`, `f/fStart/archive/**` |
| `Docs/*.md` (keep slim) | Re-expanding retired docs |

## BRAHL lifecycle

**Build → Run → Analyze → Heal → Loop → Verify → BRAHL report.**  
Run/Loop = FoXYiZ only (no LLM). Heal in yPAD first; never weaken A1 assertions.

## Naming & layout

- Engine lives in **`KK/FoXYiZ/{f,x,y,z,pyUtils}`**. From `KK/`:  
  `python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json`
- UI: `python qoa_web/run_local.py` → http://127.0.0.1:8765

## Suite habits

- Unique `PReuse_<Suite>_…` IDs; `Run=N` for pure setup reuses.
- Tags semicolon-separated; filter via fStart `"tags"`.
- After `xReuse`, parent plan must navigate (base_url / profile_url).
- Assert **visible live UI** text; **snapshot yPAD before every major expansion** (`y/<suite>/versions/`).
- Lean day smoke: `y/Math/`. Product deep example: `y/thoughtstream/` + `thoughtstream_deep.json`.

## End of session

```powershell
python FoXYiZ\pyUtils\cleaner.py --apply
python FoXYiZ\pyUtils\cleaner.py --apply --ypad-versions   # older version CSVs → archive (keep 2)
```

Optional: `--runtime-scratch` after temporary heal fStarts. Safe to delete `archive/cleanup/` anytime. Session log: [todaysummary.md](../todaysummary.md).
