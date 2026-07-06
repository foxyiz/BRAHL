# BRAHL — Prompt context (slim)

Condensed for in-app AI prompts. Full reference: [BRAHL.md](./BRAHL.md). Session hygiene: [MAINTENANCE.md](./MAINTENANCE.md).

**Formula:** `f(x, y) = z` — FoXYiZ engine + yPAD → results in `z/`.

---

## Five phases

| Phase | Folder | Goal |
|-------|--------|------|
| **Build** | `y/<suite>/` | Author y1Plans, y2Actions, y3Designs |
| **Run** | `f/fStart*.json` | Execute tagged plans → `z/<timestamp>_<suite>/` |
| **Analyze** | `z/` | Classify failures T1/T2/T3/A1 |
| **Heal** | `y/` | Fix test/engine/env issues; keep A1 strict |
| **Loop** | repeat | 3 failure-only loops → full Verify → report |

---

## yPAD layout

| File | Role |
|------|------|
| `y/<suite>/y1Plans.csv` | PlanId, DesignId, Run, Tags, Output |
| `y/<suite>/y2Actions.csv` | ActionType, ActionName, Input, Expected, Critical |
| `y/<suite>/y3Designs.csv` + `Common/yD_*.csv` | Locators and data (D1, D2, …) |
| `y/<suite>/<suite>.json` | Suite config (`input_files`) |

**Rules:** Edit CSVs directly. Tags are semicolon-separated (`qoa_web;Smoke`). Reuse plans: `Run=N`, invoke via `xReuse`. After reuse, parent plan must `xNavigate base_url`.

---

## Run

```powershell
python f/fEngine2.py --config f/fStart_qoa_web_verify.json
```

| fStart field | Use |
|--------------|-----|
| `tags` | Filter plans; `[]` = all `Run=Y` |
| `timeout` | Default 5 (verify config) |
| `headless` | false while debugging |
| `thread_count` | 1 for session/admin flows |

**Output:** `z/<run>/*_zResults.csv`, `*_zDash.html`, `_errors.csv`, `brahl_report.md`.

---

## Analyze — classify failures

Read in order: `_errors.csv` → `*_zResults.csv` → `*_zDash.html` → step artifacts.

| Class | Meaning | Action |
|-------|---------|--------|
| **T1** | yPAD (locator, Expected, order) | Heal y/ |
| **T2** | Engine (tag filter, cache, stale exe) | Fix f/ or rebuild |
| **T3** | Environment (creds, network) | Fix config / `.env` |
| **A1** | Application defect | Do not weaken test; document in report |

---

## Heal — priority order

1. `yD_Common.csv` / `yD_Secure.csv` — locators, URLs
2. `y2Actions.csv` — steps, Expected, xReuse, xNavigate (no xWaitFor)
3. `y1Plans.csv` — Run, Tags, DesignId, order
4. `f/fStart*.json` — tags, timeout, threads

**Rules:** Minimal diff. Empty `Expected` on xGetText for presence checks. Never delete assertions to force green on A1.

---

## Loop protocol

```
Loop 1  RUN full in-scope (Run=Y) → ANALYZE → HEAL
Loop 2  RUN failures only (Run=N on passes) → ANALYZE → HEAL
Loop 3  RUN remaining failures → ANALYZE → HEAL
Verify  Restore all Run=Y → full run → standard BRAHL report
```

If loop 1 is all green, still run Verify and note loops 2–3 skipped.

---

## qoa_web integration

- **PROJECT** dropdown scopes Run/Analyze/Heal/Loop/BRAHL to `y/<suite>/`.
- Personas P1–P9: `Docs/test-user-data/` (not hard-coded in UI).
- Run tab invokes local `fEngine2` subprocess; Analyze reads `z/` for selected suite.
- Reports linked on BRAHL tab: Automation, HITL, hybrid.

---

## A1 defect tags (Build)

| Tag | When |
|-----|------|
| `Issue` | 404 / broken route |
| `Link` | Dead nav or CTA |
| `Security` | Missing auth gate |
| `Element` | Required UI missing |

List A1 plans in report; do not heal away real app bugs.
