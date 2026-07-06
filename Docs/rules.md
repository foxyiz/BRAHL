# FoXYiZ / QAonAir — Agent & Team Rules

Standing conventions for humans and AI agents working in this workspace. Read this before **Build**, **explore**, or **Heal** tasks.

Related: [BRAHL.md](./BRAHL.md) · [FoXYiZ.md](./FoXYiZ.md) · [README.md](./README.md) · [HANDOFF.md](./HANDOFF.md)

---

## 1. Application exploration — Playwright only

**Do not create new Python scripts to explore or scrape applications.**

Exploration scripts (Selenium crawlers, one-off `explore_*.py` helpers, HTTP scrapers) confuse the repo, duplicate FoXYiZ, and bypass the skills we already have.

### Use instead

| Need | Tool |
|------|------|
| Live UI exploration, locators, flows | **Playwright MCP** (`browser_navigate`, `browser_snapshot`, `browser_click`, …) |
| yPAD authoring after exploration | Edit **`y/<suite>/`** CSVs + suite JSON |
| Test execution | **`python f/fEngine2.py`**, **`BRAHL.py`**, or **`Foxyiz2.exe`** |
| Lifecycle guidance | **[BRAHL.md](./BRAHL.md)**, **[FoXYiZ.md](./FoXYiZ.md)** skills |
| Plan graph / workflow view | **`python u/yVisualizer.py`** |

### Existing exploration artifacts (read-only reference)

These were created earlier; **do not add siblings or variants**:

| File | Purpose |
|------|---------|
| `explore_gosunshine.py` | Legacy Selenium explorer for Sunshine |
| `explore_gosunshine2.py` | Phased legacy explorer (routes, admin, shop, locators, mobile) |
| `gosunshine_explore_report.json` | Cached route/UI snapshot from those runs |

For **fresh** UI state, use Playwright MCP and update yPAD locators — do not re-run or extend the Python explorers unless the user explicitly asks to maintain them.

---

## 2. Default edit scope — yPAD and config only

Unless the user explicitly requests engine or tooling changes:

- **Edit:** `y/**/*.csv`, `y/**/*.json`, `f/fStart*.json`
- **Do not edit:** `fEngine2.py`, `xActions.py`, `BRAHL.py`, unless asked
- **Utilities:** `u/` folder (`cleaner.py`, `sync_personas.py`, etc.) — safe to extend

Run and analyze with the existing engine; heal failures in yPAD first (BRAHL **Heal** phase).

---

## 3. BRAHL lifecycle (required for new suites)

Every new app suite (e.g. Sunshine, qoa2) follows **Build → Run → Analyze → Heal → Loop**:

1. **Build** — y1Plans, y2Actions, y3Designs / yD_Common, suite JSON, reuse blocks, tags
2. **Run** — tagged subsets first (`Smoke` → feature tags → full suite)
3. **Analyze** — `z/_errors.csv`, `*_zResults.csv`, `*_zDash.html`, step artifacts
4. **Heal** — locators and steps in yPAD; classify T1 (test) vs A1 (app defect)
5. **Loop** — Loop 1 (full set) → Loops 2–3 (failures only) → **Verify** (full set) → **Standard BRAHL report**

Do not weaken assertions to force green. Do not declare “done” after a single run.

---

## 4. Suite patterns (follow qoa2)

When adding a new suite under `y/<name>/`:

- **`PReuse_<Suite>_OpenSite`** — `Run=N`, opens browser + navigates to `base_url`
- **Unique reuse IDs per suite** — never share `PReuse_OpenSite` across apps
- **Session-aware steps** — after login, prefer `xNavigate,<url>` over cached login reuse
- **Tags** — semicolon-separated (`sunshine;Smoke;Shop`); filter via `fStart.json`
- **Credentials** — `yD_Secure.csv` or `.env`; never commit secrets in plan names
- **Admin before customer** in full-suite order when personas conflict (same lesson as qoa2 D2/D1)

Template reference: `y/qoa2/`.

---

## 5. What agents must not do

- Create **`explore_*.py`**, **`scrape_*.py`**, or ad-hoc Selenium/requests crawlers for app discovery
- Spawn subagents whose main job is writing Python explorers
- Add Python **generators** for yPAD CSVs unless the user explicitly requests them
- Modify frozen exe assumptions without noting `fEngine2.py` vs `Foxyiz2.exe` alignment
- Run the full suite while iterating a single locator fix — use tags

---

## 6. What agents should do

- Read **`Docs/README.md`**, **`Docs/BRAHL.md`**, and **`Docs/FoXYiZ.md`** at the start of suite work
- Explore with **Playwright MCP**; capture routes, headings, buttons, stable locators
- Reuse **`gosunshine_explore_report.json`** (or similar) as a **starting point**, then verify live
- Run **`python f/fEngine2.py --config f/fStart_<tag>.json`**, analyze `z/`, heal yPAD, loop
- Report pass rate, heals applied, and remaining A1 defects with evidence

---

## One-line summary

**Explore with Playwright; automate with FoXYiZ yPAD; loop BRAHL until the tests are right — not the app wrong.**
