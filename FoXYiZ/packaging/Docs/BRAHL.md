# BRAHL — Build · Run · Analyze · Heal · Loop

Packaged FoXYiZ quick reference. Spellings: **FoXYiZ** · **BRAHL** · **yPAD**.

## Formula

```
f(x, y) = z
```

| Symbol | Folder | Role |
|--------|--------|------|
| **f** | `f/` | Engine + `fStart` configs |
| **x** | `x/` | Capabilities (`xCapa.csv` catalog; handlers inside the exe) |
| **y** | `y/<suite>/` | Your tests (yPAD CSVs) |
| **z** | `z/` | Results |

## Lifecycle

```
Build (yPAD) → Run (exe) → Analyze (z/) → Heal (yPAD) → Loop → Verify → report
```

| Phase | Job |
|-------|-----|
| **Build** | Author `y1Plans` / `y2Actions` / `y3Designs` + suite JSON + fStart |
| **Run** | `.\f\FoXYiZ.exe --config f\fStart\<suite>.json` |
| **Analyze** | Read `*_zResults.csv`, `_errors.csv`, `*_zDash.html` |
| **Heal** | Fix test defects (T1–T3). Leave A1 (app bugs) strict |
| **Loop** | Re-run failures → restore Run=Y → Verify |
| **Report** | Go/No-Go in `brahl_report.md` (`## Conclusion`) |

### Loop protocol

```
Loop 1   full Run=Y → analyze → heal
Loop 2   Run=N on passes → failures only → heal
Loop 3   remaining failures → heal
Verify   restore all Run=Y → full run → BRAHL report
```

## Failure classes

| Code | Meaning | Action |
|------|---------|--------|
| **T1** | Flaky / wait / locator | Heal yPAD |
| **T2** | Wrong Expected / design data | Heal yPAD |
| **T3** | Suite / config / tag issue | Heal fStart or tags |
| **A1** | Real **app** defect | Document; do **not** weaken asserts |

## GO / NO-GO

- **GO** — Verify green for scoped tags  
- **NO-GO** — fails remain; heal or document A1  

## yPAD files

| File | Role |
|------|------|
| `y1Plans.csv` | Plans: `PlanId`, `DesignId`, `Run`, `Tags`, `Output` |
| `y2Actions.csv` | Steps: `ActionType`, `ActionName`, `Input`, `Expected`, `Critical` |
| `y3Designs.csv` | Data: `DataName` + **D1…D9** persona columns |

Personas only in **D1–D9**. Action names must exist in `x/xCapa.csv`.

## Common tags

`Smoke` · `UI` · `Func` · `Edge` · `Security` · `API` · `Perf` · `Manual` · `BRAHL` · `Conclusion` · `Reuse`
