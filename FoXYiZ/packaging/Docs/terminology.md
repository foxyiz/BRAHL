# Terminology — FoXYiZ package

Use these spellings exactly.

## Core names

| Term | Spell | Meaning |
|------|-------|---------|
| **FoXYiZ** | F-o-X-Y-i-Z | Automation engine + folders `f` · `x` · `y` · `z` |
| **BRAHL** | B-R-A-H-L | **B**uild → **R**un → **A**nalyze → **H**eal → **L**oop (+ Verify) |
| **yPAD** | y-P-A-D | `y1Plans`, `y2Actions`, `y3Designs` |
| **fStart** | — | Run config JSON under `f/fStart/{suite}.json` |
| **z / zResults / zDash** | — | Run output under `z/` |

## Formula

```
f(x, y) = z
```

## Verbs

| Say | Means |
|-----|-------|
| **brawl** / **brawled** | Full BRAHL cycle to Verify |
| **smoke** | Launch-readiness shell only |
| **deep** | Beyond smoke (Func / Edge / Security / API / Perf) |
| **heal** | Fix a **test** defect (T1–T3); never weaken A1 |
| **verify** | Final full Run=Y after Loop — GO/NO-GO gate |

## Failure classes

| Code | Owner |
|------|-------|
| **T1** | Flaky / wait / locator → heal yPAD |
| **T2** | Wrong Expected / design → heal yPAD |
| **T3** | Suite / config / tags → heal fStart |
| **A1** | Real app defect → document only |

## Package paths

```powershell
.\f\FoXYiZ.exe --config f\fStart\<suite>.json
```

Engine resolves `y/…` and `z/…` from the package root (parent of `f/` when the exe lives in `f/`).
