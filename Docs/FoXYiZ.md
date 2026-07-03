---
name: foxyiz
description: >-
  Expert guide for the FoXYiZ LCNC automation framework (f(x,y)=z). Use when
  creating or editing YPAD files (y1Plans, y2Actions, y3Designs), configuring
  fStart.json, running Foxyiz.exe/f2.exe, analyzing z/ results, healing test
  failures, building web/API/math suites, or any question about xUI, xAPI, xMath,
  xReuse, tags, parallel runs, or Base44 app automation. Trigger on foxyiz, YPAD,
  yPAD, create a plan, add a step, fix failure, analyze results, fStart, zResults.
---

# FoXYiZ Skill

You are an expert on **FoXYiZ** — a low-code/no-code automation framework.

**Formula:** `f(x, y) = z`

| Symbol | Meaning |
|--------|---------|
| **f** | Engine (`Foxyiz2.exe`, `python f/fEngine2.py`, or `BRAHL.py`) |
| **x** | Built-in capabilities (`xUI`, `xAPI`, `xMath`, `xJSON`, `xAI`, `xReuse`) |
| **y** | User automation files under `y/` (Plans, Actions, Designs) |
| **z** | Results under `z/` (CSV, HTML dashboard, error logs) |

**Default scope for agents:** edit **yPAD CSV/JSON and `f/fStart.json` only**. Do not modify `fEngine.py`, `xActions.py`, or executables unless the user explicitly asks.

---

## When to apply this skill

| User intent | Start here |
|-------------|------------|
| Create a new test suite | [New suite checklist](#new-suite-checklist) |
| Add plans or steps | [YPAD file contract](#ypad-file-contract) |
| Fix a failing run | [Heal workflow](#heal-workflow) |
| Run tests | [Execution](#execution) |
| Multi-app / parallel runs | [Parallel rules](#parallel-rules) |
| Lifecycle / lessons learned | [BRAHL.md](./BRAHL.md) |

---

## Project layout (July2 / qoa2)

```
July2/
├── BRAHL.py                # Desktop GUI — Build/Run/Analyze/Heal/Loop
├── f/
│   ├── Foxyiz2.exe         # Frozen runner (rebuilt from fEngine2.py)
│   ├── fEngine2.py         # Dev engine
│   ├── fStart.json         # Run config (tags, thread_count)
│   └── fGUI.py             # Run-only GUI
├── x/xActions.py, xCapa.csv, xCustom.py
├── y/qoa2/                 # qoa2 yPAD suite
└── z/<timestamp>_qoa2/     # *_zResults.csv, *_zDash.html, _errors.csv
```

---

## YPAD file contract

### y1Plans.csv — what runs

**Columns:** `PlanId, PlanName, DesignId, Run, Tags, Output`

| Column | Rules |
|--------|-------|
| `PlanId` | Unique, no spaces (`PWeb_Login_Link`) |
| `DesignId` | `D1` or `D1;D2;D3` for multi-design runs |
| `Run` | `Y` = execute, `N` = skip (reuse plans, optional perf) |
| `Tags` | Semicolon-separated; filtered by `fStart.json` `"tags"` |

```csv
PlanId,PlanName,DesignId,Run,Tags,Output
PReuse_MyApp_OpenSite,Open browser and navigate,D1,N,Reuse,site_loaded
PWeb_Landing_Verify,Verify landing page,D1,Y,MyApp;Smoke;Landing,landing_ok
```

### y2Actions.csv — how it runs

**Columns:** `PlanId, StepId, StepInfo, ActionType, ActionName, Input, Output, Expected, Critical`

| Column | Rules |
|--------|-------|
| `Input` | Semicolon-separated; tokens resolve from Designs `DataName` |
| `Output` | Variable stored for later steps in the same plan |
| `Expected` | Comparison target (optional) |
| `Critical` | `y` = stop plan on fail; `n` = continue |

```csv
PlanId,StepId,StepInfo,ActionType,ActionName,Input,Output,Expected,Critical
PWeb_Landing_Verify,1,Open site,xReuse,PReuse_MyApp_OpenSite,,,,y
PWeb_Landing_Verify,2,Verify h1 text,xUI,xGetText,h1_locator,h1_text,,y
```

### y3Designs / yD_Common.csv — data and locators

**Columns:** `Type, DataName, D1, D2, D3, …` (extend D4–D6 as needed)

```csv
Type,DataName,D1,D2,D3
UI,base_url,https://app.example.com/,https://staging.example.com/,https://dev.example.com/
UI,h1_locator,css=h1,css=h1,css=h1
UI,login_url,https://app.example.com/login,https://staging.example.com/login,https://dev.example.com/login
```

**Locators:** prefix with `css=`, `xpath=`, or `id=` (e.g. `css=a[href='/login']`).

### Suite JSON

```json
{
  "input_files": {
    "yPlans":   ["y/MyApp/y1Plans.csv"],
    "yActions": ["y/MyApp/y2Actions.csv"],
    "yDesigns": ["y/MyApp/Common/yD_Common.csv", "y/MyApp/y3Designs.csv"]
  }
}
```

Files merge in list order — later files append rows.

---

## xReuse — the most important pattern

Every web suite needs a **reuse plan** per suite:

```
PReuse_<Suite>_OpenSite  (Run=N, Tags=Reuse)
  1. xOpenBrowser, edge
  2. xNavigate, base_url   ← waits for body automatically
```

Every UI plan starts with: `xReuse, PReuse_<Suite>_OpenSite`

### Critical rules

1. **Unique ID per suite** — `PReuse_JusDone_OpenSite`, never shared `PReuse_OpenSite`. Shared IDs break parallel multi-suite runs.
2. **Reuse does not re-navigate** — once cached for the browser session, only the open-browser steps are skipped. The browser stays on whatever page the last plan left it on.
3. **Always reset state when unsure** — add `xNavigate,base_url` (or `login_url`, etc.) before clicks on home-page elements.
4. **Prefer direct URL navigation** over nav clicks for content verification when prior plans may have changed URL.

---

## ActionType reference

### xUI — browser

| ActionName | Input | Notes |
|------------|-------|-------|
| `xOpenBrowser` | `edge` or `chrome` | Prefer `edge` on Windows |
| `xCloseBrowser` | — | Kills session; avoid in shared parallel runs |
| `xNavigate` | `url_variable` | Most reliable state reset |
| `xClick` | `locator` | Waits for element (uses `timeout` from `fStart.json`) |
| `xType` | `value;locator` | Waits for element |
| `xGetTitle` | — | Output → page title |
| `xGetText` | `locator` | Output → element text; use to verify an element is present |
| `xGetAttribute` | `locator;attribute` | e.g. `input_css;value` |
| `xStartTimer` / `xStopTimer` | output var | For perf plans |
| `xAssertLessThan` | `actual;max` | Perf threshold check |

**Not available in all builds:** `xClear` — use `xNavigate,base_url` + fresh `xType` instead.

**Do not use `xWaitFor`:** Removed from `x/xCapa.csv`. It caused flaky timeouts in web/UI suites. Use `xNavigate` (waits for body), `xGetText` (verify presence), or `xClick`/`xType` (auto-wait via `timeout` in `fStart.json`) instead.

### xMath

| ActionName | Input |
|------------|-------|
| `xAdd`, `xMultiply` | `a;b` or `a;b;c` |
| `xDiv`, `xModulo` | `a;b` |
| `xPower` | `base;exponent` |
| `xRound` | `number;decimal_places` |

### xAPI

| ActionName | Input | Expected |
|------------|-------|----------|
| `xGet` | `base_url;endpoint` | HTTP status |
| `xPost` / `xPut` | `base_url;endpoint;payload_file` | HTTP status |
| `xDelete` | `base_url;endpoint` | HTTP status |

### xJSON (last API response)

| ActionName | Input |
|------------|-------|
| `xValidateJson` | `json_key_path` |
| `xExtractJson` | `json_key_path` |
| `xCompareJson` | `json_key_path;value` |

### xReuse

| ActionName | Input |
|------------|-------|
| `<PlanId>` | empty |

Inlines the target plan's steps at this step.

---

## Execution

### fStart.json

```json
{
  "configs": [
    "y/JusDone/JusDone.json",
    "y/Nalanda/Nalanda.json"
  ],
  "thread_count": 6,
  "timeout": 10,
  "headless": false,
  "debug": false,
  "tags": []
}
```

| Field | Purpose |
|-------|---------|
| `configs` | List of suite JSON paths |
| `thread_count` | Parallel threads (`1` = sequential, `N` = one thread per config) |
| `timeout` | Default wait seconds for UI actions (`xNavigate`, `xClick`, `xType`, `xGetText`, etc.) |
| `headless` | `false` for visible browser (debugging) |
| `tags` | Run only plans whose `Tags` column contains any listed tag; `[]` = all |

### Commands

From `Demo-main/`:

```powershell
# Sequential — debug / first heal pass
python f\fEngine.py --config f\fStart.json

# Single suite
python f\fEngine.py --config y\JusDone\JusDone.json

# Executables (from f/ folder)
cd f
.\Foxyiz.exe --config fStart.json    # sequential
.\f2.exe --config fStart.json        # parallel
```

**Encoding note:** `Foxyiz.exe` / `f2.exe` may crash with `UnicodeEncodeError` in some terminals. Use `python f\fEngine.py` or run from a normal PowerShell window.

### Tag filters

| Goal | fStart `"tags"` |
|------|-----------------|
| Fast smoke | `["Smoke"]` |
| Auth only | `["Auth"]` |
| Stateful flows | `["Regression"]` |
| Full suite | `[]` |

---

## Parallel rules

| Rule | Why |
|------|-----|
| One `PReuse_<Suite>_OpenSite` per suite | Prevents reuse cache collisions |
| Perf plans: `Run=N` | `xCloseBrowser` kills the browser for that thread |
| `xNavigate,base_url` before home clicks | Prior plans may leave browser on `/login`, `/register`, etc. |
| Sequential green before parallel | Isolates yPAD issues from threading issues |

---

## Agent workflow

```
Explore app → Write yPAD → Run engine → Read z/_errors.csv → Fix yPAD → Repeat
```

### Do / Don't

| Do | Don't |
|----|-------|
| Edit yPAD CSVs, suite JSON, `fStart.json` | Edit engine Python unless asked |
| Use suite-scoped reuse plan IDs | Share reuse IDs across suites |
| Add `xNavigate` when browser state is uncertain | Assume reuse resets the page |
| Read `_errors.csv` and artifact links | Guess locators |
| Set perf plans `Run=N` in shared runs | Enable `xCloseBrowser` plans in parallel |
| Match existing column headers and conventions | Invent new columns or action types |

### New suite checklist

1. Create `y/<Suite>/` with `y1Plans.csv`, `y2Actions.csv`, `Common/yD_Common.csv`, `<Suite>.json`.
2. Add `PReuse_<Suite>_OpenSite` (`Run=N`, tag `Reuse`).
3. Build plans in layers: **Smoke → Navigation → Auth → Interaction → Content → Regression**.
4. Tag every plan; include `Smoke` on fast checks.
5. Add URL variables: `base_url`, `login_url`, `register_url`, route-specific URLs.
6. Register in `f/fStart.json` → `configs`.
7. Run smoke (`"tags": ["Smoke"]`), heal, then full suite.

### Web plan template

Typical smoke plan steps:

```
xReuse  → PReuse_<Suite>_OpenSite
xGetText → h1_locator
xGetText → nav_locator (or key UI element)
```

Typical auth plan steps:

```
xReuse  → PReuse_<Suite>_OpenSite
xNavigate → base_url          ← reset if prior plans changed URL
xClick  → login_link_locator
xGetText → login_form_locator  ← verify page loaded (or xGetTitle)
```

Typical regression roundtrip:

```
xReuse → PReuse_<Suite>_OpenSite
xNavigate → base_url
xClick → off_page_link
xNavigate → base_url
xClick → another_link
xNavigate → base_url
xGetText → h1_locator
```

---

## Heal workflow

### Steps

1. Open `z/<timestamp>_<Suite>/_errors.csv`.
2. Record `PlanId`, `StepId`, `ActionName`, `Input`, error text.
3. Open linked screenshot/page dump if present.
4. Reproduce with `"headless": false`.
5. Apply smallest yPAD fix.
6. Re-run single suite, then full `fStart.json`.

### Diagnosis table

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Element not found after auth plan | Browser on sub-page; reuse skipped navigate | `xNavigate,base_url` before click |
| Passes sequential, fails parallel | Missing navigate or shared reuse ID | Unique reuse ID + navigate home |
| Element not found / timeout on `xGetText` or `xClick` | Wrong locator or slow page | Fix locator; increase `timeout` to 10–30 |
| `Unknown xUI action: xClear` | Action not in engine | Navigate + re-type |
| `footer` / `main` / `header a` missing | Element not in DOM | Use `body` or direct URL |
| Button click fails | Disabled until input present | Type text before click |

---

## Base44 reference suites (Demo-main)

| Folder | App | URL | Plans |
|--------|-----|-----|-------|
| `JusDone/` | ThoughtStream | https://jusdone.base44.app/ | 14 |
| `Nalanda/` | Nalanda | https://nalanda.base44.app/ | 15 |
| `Varkasa2/` | Varkasa | https://varkasa2.base44.app/ | 12 |
| `BRAHL_Base44/` | QAonAir2 | https://brahl.base44.app/ | 12 |
| `Atomic77/` | Atomic 77 | https://atomic77.base44.app/ | 11 |
| `FlowPilot/` | FlowPilot | https://foxyiz-ai.base44.app/ | 11 |

Use these as copy templates for new web suites. Full lifecycle notes: [BRAHL.md](./BRAHL.md).

---

## Minimal math example

**y1Plans.csv**
```csv
PlanId,PlanName,DesignId,Run,Tags,Output
PAdd,Verify Addition,D1;D2,Y,Math,result
```

**y2Actions.csv**
```csv
PlanId,StepId,StepInfo,ActionType,ActionName,Input,Output,Expected,Critical
PAdd,1,Add numbers,xMath,xAdd,num1;num2,vResult,vResult,n
```

**y3Designs.csv**
```csv
Type,DataName,D1,D2
Math,num1,10,100
Math,num2,5,50
Math,vResult,15,150
```

Run: `python f\fEngine.py --config y\Math\Math.json`

---

## Related docs

| Doc | Contents |
|-----|----------|
| [BRAHL.md](./BRAHL.md) | Build → Run → Analyze → Heal → Loop; session learnings |
| [ypad-concepts.md](./ypad-concepts.md) | f(x,y)=z mental model, merge order, DesignId |
| [prompts.md](./prompts.md) | LLM prompt templates for build/analyze/heal |
| [evals.md](./evals.md) | Reading z/ results, quality bars |
| [FoXYiZ_vs_Playwright.md](./FoXYiZ_vs_Playwright.md) | LCNC vs Playwright; when to use which; hybrid strategy |
| [FoXYiZ_Market_Position.md](./FoXYiZ_Market_Position.md) | vs Karate, Selenium, Tosca; strategic outlook |
| [TOPICS.md](./TOPICS.md) | Full documentation map |

---

## Quick reference card

```
Files:     y1Plans (what) + y2Actions (how) + yD_Common (data/locators)
Reuse:     PReuse_<Suite>_OpenSite — unique per suite, Run=N
Reset:     xNavigate,base_url before home-page clicks
Run all:   python f\fEngine.py --config f\fStart.json
Failures:  z/<timestamp>_<Suite>/_errors.csv
Heal:      yPAD only — locators in yD_Common, steps in y2Actions
Parallel:  f2.exe + thread_count = # configs; perf plans Run=N
Tags:      Smoke | Navigation | Auth | Interaction | Content | Regression
```
