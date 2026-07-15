# Agent & team rules (KK)

Standing conventions for humans and AI working in this workspace.

Related: [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) · [AI_GUARDRAILS.md](./AI_GUARDRAILS.md) · [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md)

## Explore apps with Playwright MCP

Do **not** add one-off Python scrapers. Use Playwright (`browser_navigate`, `browser_snapshot`, …), then edit **yPAD** CSVs.

## Default edit scope

| Touch | Avoid unless asked |
|-------|--------------------|
| `qoa_web/web/*`, `qoa_web/api/*` | `FoXYiZ/f/fEngine2.py`, `FoXYiZ/x/xActions.py` |
| `FoXYiZ/y/<suite>/*.csv`, `*.json` | Dumping `FoXYiZ/z/**` into chat |
| `FoXYiZ/f/fStart_*.json` | `archive/**` |

## BRAHL lifecycle

**Build → Run → Analyze → Heal → Loop → BRAHL report.**  
Run/Loop = FoXYiZ only (no LLM). Heal in yPAD first; never weaken A1 assertions.

## Naming & layout

- Always **BRAHL** · **FoXYiZ**.
- Engine lives in **`KK/FoXYiZ/{f,x,y,z,pyUtils}`**. From `KK/`:  
  `python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json`
- UI: `python qoa_web/run_local.py` → http://127.0.0.1:8765

## Suite habits

- Unique `PReuse_<Suite>_…` IDs; `Run=N` for pure setup reuses.
- Tags semicolon-separated; filter via fStart `"tags"`.
- After `xReuse`, parent plan must navigate (base_url / profile_url).
- Lean day-to-day smoke: `y/Math/`, `y/nalanda_app/`. Gate: `y/qoa_web_live/` (cite paths only — no 800-plan CSVs in chat).

## End of session

```powershell
python FoXYiZ\pyUtils\cleaner.py --apply
```

Safe to delete `archive/cleanup/` anytime. Session log: [todaysummary.md](../todaysummary.md).
