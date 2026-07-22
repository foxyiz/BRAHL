---
name: brahl
description: >-
  BRAHL lifecycle: Build yPAD, Run FoXYiZ.exe, Analyze z/, Heal test defects
  (T1–T3), Loop, Verify to GO/NO-GO. Use when triaging failures, writing
  brahl_report.md, or explaining Build/Run/Analyze/Heal/Loop. Trigger on BRAHL,
  brawl, heal, loop, verify, A1, T1, zResults, zlogs, Go/No-Go.
---

# BRAHL — Build · Run · Analyze · Heal · Loop

Quality lifecycle for **FoXYiZ** automation and **QA on Air** Arena phases.

Spellings: **BRAHL** · **FoXYiZ** · **yPAD** · verb **brawl** / **brawled**.

## Skill

| Field | Value |
|-------|-------|
| **Skill id** | `brahl` |
| **Primary users** | Creator (Champion), QA Hunter (Contender), automation agents |
| **Apply when** | Authoring or healing suites; classifying T1–T3 vs A1; Loop/Verify; writing `brahl_report.md` |
| **Do not use for** | Editing frozen engine binaries; marketplace wallet/billing details → [QAonAir.md](QAonAir.md) |
| **Related skills** | `foxyiz` (how to run/author) · `qaonair` (Arena / product surface) |
| **Triggers** | BRAHL, brawl, heal, loop, verify, T1, T2, T3, A1, GO, NO-GO, zlogs, brahl_report |

**Hard rule:** Run / Loop / Verify = **FoXYiZ.exe only** — never the LLM. AI may assist Build, Analyze, Heal, and report chat.

---

## Formula

```
f(x, y) = z
```

| Symbol | Folder | Role |
|--------|--------|------|
| **f** | `f/` | Engine (`FoXYiZ.exe` + `_internal`) + `fStart` |
| **x** | `x/` | Capability catalog (`xCapa.csv`) |
| **y** | `y/<suite>/` | yPAD tests |
| **z** | `z/` | Results + **zlogs** |

---

## Lifecycle

```
Build → Run → Analyze → Heal → Loop → Verify → Report
```

| Phase | Job | FoXYiZ? | AI? |
|-------|-----|---------|-----|
| **Build** | Author y1/y2/y3 + suite JSON + fStart | Reads/writes `y/` | Optional |
| **Run** | `.\f\FoXYiZ.exe --config f\fStart\<suite>.json` | **Yes** | **Never** |
| **Analyze** | Read zResults, zDash, `_errors`, **zlogs** | Reads `z/` | Optional RCA |
| **Heal** | Fix T1–T3 in yPAD/fStart; keep A1 strict | Writes `y/` | Optional |
| **Loop** | L1 full → L2–L3 failures-only | **Yes** | **Never** |
| **Verify** | Restore Run=Y; full regression | **Yes** | **Never** |
| **Report** | GO/NO-GO in `brahl_report.md` | Reads report | Optional Q&A |

### Loop protocol

```
Loop 1   full Run=Y → analyze → heal
Loop 2   Run=N on passes → failures only → heal
Loop 3   remaining failures → heal
Verify   restore all Run=Y → full run → BRAHL report
```

### Failure classes

| Code | Meaning | Action |
|------|---------|--------|
| **T1** | Flaky / wait / locator | Heal yPAD |
| **T2** | Wrong Expected / design | Heal yPAD |
| **T3** | Suite / config / tags | Heal fStart |
| **A1** | Real **app** defect | Document only — never weaken asserts |

### z artifacts (per run)

| File | Role |
|------|------|
| `{suite}_zResults.csv` | Per-step Pass/Fail |
| `_errors.csv` | Failure index |
| `{suite}_zDash.html` | Dashboard |
| **`zlogs.txt`** | Console transcript |
| `brahl_report.md` | After Verify — Conclusion GO/NO-GO |

Flat index: `z/zlogs.txt`. Optional helpers: `_pyUtils/` (needs Python) — see [FoXYiZ.md](FoXYiZ.md).

### yPAD (Build)

| File | Role |
|------|------|
| `y1Plans.csv` | What: PlanId, Run, Tags, DesignId |
| `y2Actions.csv` | How: ActionType, ActionName, Expected, Critical |
| `y3Designs.csv` | Data: DataName + D1…D9 |
| `<suite>.json` | `input_files` + metadata |

Tags: `Smoke` · `UI` · `Func` · `Edge` · `Security` · `API` · `Perf` · `Manual` · `BRAHL` · `Conclusion` · `Reuse`

---

## See also

- [FoXYiZ.md](FoXYiZ.md) — package layout, exe, `_pyUtils`
- [QAonAir.md](QAonAir.md) — Arena / marketplace framing
