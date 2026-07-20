# Terminology — KK / FoXYiZ / BRAHL

Spellings and verbs used in this workspace. Agents and humans use these **exactly** so runs and reports stay consistent.

---

## Core names

| Term | Spell | Meaning |
|------|-------|---------|
| **FoXYiZ** | F-o-X-Y-i-Z | Automation engine + folders `f` · `x` · `y` · `z`. **Not** “Foxyiz”, “FoxYiZ”, “foxyiz” in docs. |
| **BRAHL** | B-R-A-H-L | Lifecycle: **B**uild → **R**un → **A**nalyze → **H**eal → **L**oop (+ Verify + report). **Not** “Brawl”, “BRAHL cycle” misspelled as “bral”. |
| **Arena** | — | Local web UI (`qoa_web`) at http://127.0.0.1:8765 — drives BRAHL over FoXYiZ. |
| **yPAD** | y-P-A-D | The three CSV “white pads”: **y1Plans**, **y2Actions**, **y3Designs**. |
| **fStart** | — | Run config JSON under `FoXYiZ/f/fStart/{suite}.json` (one file per suite). |
| **z / zResults / zDash** | — | Run output folder, CSV results, HTML dashboard under `FoXYiZ/z/`. |

---

## Formula

```
f(x, y) = z
```

| Symbol | Folder | Role |
|--------|--------|------|
| **f** | `FoXYiZ/f/` | Engine (`fEngine2.py`) + fStart configs |
| **x** | `FoXYiZ/x/` | Built-in actions (`xUI`, `xAPI`, `xMath`, `xReuse`, …) |
| **y** | `FoXYiZ/y/<suite>/` | Your tests (yPAD) |
| **z** | `FoXYiZ/z/` | Ephemeral results (archive with cleaner) |

---

## Verbs (how we talk about work)

| Say | Means |
|-----|--------|
| **brawl** / **brawled** | Ran a full BRAHL cycle (Build→…→Verify + report). *“We brawled ThoughtStream deep — GO.”* |
| **smoke** | Tag/`Run` profile: launch-readiness shell only. |
| **deep** | Func + Edge + Security + API + Perf (and similar) — beyond smoke. |
| **heal** | Minimal yPAD CSV fix for a **test** defect (T1–T3). Never weaken A1. |
| **verify** | Final full Run=Y restore after Loop — the GO/NO-GO gate. |
| **archive** | Move old `z/` runs out of KK via `pyUtils/cleaner.py` → `../archive/cleanup/`. |
| **snapshot** | Immutable copy of yPAD CSVs under `y/<suite>/versions/<YYYYMMDD_HHMMSS>_<label>/`. **Required before every major yPAD expansion.** |
| **archive versions** | `cleaner.py --apply --ypad-versions` moves older snapshots to `../archive/cleanup/` (out of AI context); keeps newest N (default 2). |

---

## Failure classes (Analyze)

| Code | Owner | Action |
|------|-------|--------|
| **T1** | Flaky / wait / locator | Heal yPAD |
| **T2** | Wrong Expected / design data | Heal yPAD |
| **T3** | Suite/config/tag issue | Heal fStart or tags |
| **A1** | Real **app** defect | Document in BRAHL report; **do not** weaken assertions |

---

## GO / NO-GO

- **GO** — Verify green for the scoped tags; automation ready to publish for that scope.
- **NO-GO** — Verify has fails; heal or document A1 before launch readiness.
- Conclusion lives in `brahl_report.md` (`## Conclusion`).

---

## Personas & designs

| Speak | CSV |
|-------|-----|
| Persona portfolio | y3 **D1…D9** columns |
| P1–P9 (Docs test-user-data) | Map to D1–D9 |
| Guest Capturer / Researcher / Integrator | ThoughtStream D1 / D2 / D3 names |

---

## Tags (common)

`Smoke` · `UI` · `Func` · `Edge` · `Security` · `API` · `Perf` · `Manual` · `BRAHL` · `Conclusion` · `Reuse`

fStart `"tags": [...]` **filters** which Run=Y plans execute.

---

## Paths (from `KK/`)

```powershell
python FoXYiZ\f\fEngine2.py --config f/fStart/<suite>.json
python FoXYiZ\pyUtils\cleaner.py --apply
python qoa_web\run_local.py
```

Engine resolves short `f/` · `y/` · `z/` under `FoXYiZ/`.

---

## Do not confuse

| Wrong | Right |
|-------|-------|
| Brawl report | **BRAHL** report |
| FoxyIs / fox eyes | **FoXYiZ** |
| “Run AI on the suite” | Run = **engine only**; AI assists Build/Analyze/Heal |
| Commit `z/` | Archive `z/`; commit yPAD + docs when asked |
