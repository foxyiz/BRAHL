# BRAHL Web — User & AI Guide

**qoa_web** is the local web app for the BRAHL testing lifecycle: **Build → Run → Analyze → Heal → Loop → BRAHL**, plus **QA Hunters** and a **cost meter ($)**.

- **URL (local):** http://127.0.0.1:8765  
- **Formula:** f(x, y) = z — FoXYiZ runs your **yPAD** files and writes results to **z/**  
- **This doc:** for end users, QA, and AI assistants working in the app or codebase  

---

## 1. What problem does it solve?

| Who | Goal |
|-----|------|
| **Creator** | Post a challenge to the arena, set budget, run automation, review BRAHL reports, invite QA Hunters |
| **QA Hunter** | Join open challenges, explore manually, upload tests offline, submit enriched BRAHL reports |
| **Admin** | View ecosystem health (About → Admin) |

BRAHL automation (AI + FoXYiZ) handles bulk coverage. QA Hunters add real journeys, UX findings, and security issues AI misses.

---

## 2. First visit — invite trial & personas

### Invite landing (`/welcome`)

New users enter an **invite code** (from email or admin batch). A valid code starts a **7-day trial** stored in `localStorage`. Demo codes:

- `QOA-CR5-001-001-DEMO` — Creator cohort  
- `QOA-QH5-001-001-DEMO` — QA Hunter cohort  

Dev bypass: `/app?demo=1` or the footer bypass on welcome (local only).

### Sign-in page (`/signin`)

After trial (or bypass), pick a **test profile** (P1–P9). No password — choice stored in `localStorage`. The page shows a compact persona grid; long blurbs are behind **More…**.

**Profile chip** (arena top right, e.g. `P2 · Jordan Lee`) — click anytime to switch persona.

### Nine test personas (P1–P9)

Full fictional data lives in **`Docs/test-user-data/`** (source of truth). Each persona maps to a FoXYiZ design column **D1–D9** in `y/qoa_web/y3Designs.csv`.

| Code | Name | Role | Default view |
|------|------|------|--------------|
| **P1** | Alex Chen | MVP Creator | Creator only — AI chat, budget, invite QA Hunter |
| **P2** | Jordan Lee | Creator + sometimes QA Hunter | Dual — switch **C** ↔ **H** in top bar |
| **P3** | Sam Rivera | QA Hunter | QA Hunter only — join projects, deliverables |
| **P4** | Dr. Priya Nair | Senior QA Hunter | QA Hunter — tier banner, yPAD / hybrid reports |
| **P5** | Chris Martinez | Non-technical | Creator — **AI locked off**, manual Build |
| **P6** | Morgan Admin | Platform admin | Creator + QA Hunter + **Admin** page |
| **P7** | Taylor Kim | Power Creator | Creator — yPAD editor, fStart, `.md` AI docs |
| **P8** | Riley Okonkwo | Bug-bounty QA Hunter | QA Hunter — critical issues focus |
| **P9** | Casey Nguyen | **First-time user** | Empty state — no preloaded project |

**Avatar permissions:** each profile declares `allowed_avatars`. Client-only profiles (e.g. **P1 Alex Chen**) intentionally cannot switch to QA Hunter/Nalanda — those avatar buttons appear **disabled with a tooltip** ("switch profile at Sign-in for dual-role access"), not a silent no-op. Dual-role personas (P2 Jordan Lee) can switch freely.

**Deep-links (testing):**

```
http://127.0.0.1:8765/welcome?code=QOA-CR5-001-001-DEMO
http://127.0.0.1:8765/app?profile=p2&suite=qoa_web&demo=1
http://127.0.0.1:8765/app?profile=p9&demo=1
http://127.0.0.1:8765/app?reset=1&demo=1
```

**Persona badge** — compact pill below the status bar: `P6 · Morgan Admin · Creator`. Click **Tips** to expand demo tasks; **×** dismisses for the session. **Persona tips** in the context strip reopens it. Data from `GET /api/test-users/{id}/tasks`.

---

## 3. Top bar — same layout for every profile

The UI is **unified** across personas. Only permissions and visible sections change — not the shell.

```
[ Brand ]  [ C Creator ] [ H QA Hunter ] [ N Nalanda ]  [ My challenge / Open challenges ▼ ]  [ AI on ] [.md]  [ P? · Name ] [ About ] [ Admin ]
```

| Control | Meaning |
|---------|---------|
| **C — Creator** | Post challenges, budget, AI chat, invite QA Hunters, yPAD (if allowed), BRAHL phases |
| **H — QA Hunter** | Join challenges, read Creator context, submit deliverables, hunt evidence |
| **N — Nalanda** | Free knowledge community — **Learn · Teach · Discuss · Invite** (single Nalanda tab; no BRAHL phases) |
| **Challenge dropdown** | Creator: **My challenge** · QA Hunter: **Open challenges** (same control, different label) |
| **AI on/off** | Enables Build chat, Analyze/Heal AI, BRAHL Q&A. Locked for P5 |
| **.md** | Opens shared AI context documents (BRAHL, FoXYiZ, rules, this guide) |
| **Profile chip** | Return to `/signin` to switch persona |

All profiles can switch avatars where the UI allows (e.g. P2 dual Creator/QA Hunter). Dimmed avatar = that role is restricted for the persona.

---

## 4. BRAHL phases (main tabs)

All phases except Build require a **selected project** in the top bar.

| Tab | What you do | AI? |
|-----|-------------|-----|
| **Build** | Purpose, budget, connectors, yPAD explorer, QA Hunter invites, change requests | AI chat when on |
| **Run** | FoXYiZ `fEngine2` — pick fStart config, run engine | No — automation only |
| **Analyze** | Refresh **z/** runs, classify failures (T1/T2/T3/A1) | Optional AI root-cause |
| **Heal** | Edit yPAD, shrink/restore plans for Loop | Optional AI suggestions |
| **Loop** | Step 0 context, Loop 1–3, Verify, generate BRAHL report | FoXYiZ runs |
| **BRAHL** | Report list, markdown view, chat with BRAHL model; **Go/No-Go** launch verdict; **version compare** (baseline vs new) | Chat when AI on |
| **$** | Cost meter (Creator) or QA Hunter wallet | — |
| **Nalanda** | Community — learn paths, teach lessons, discuss, invite friends | FAQ chips (no AI key required) |

When avatar is **Nalanda**, only the **Nalanda** tab shows — BRAHL, A77, and **$** are hidden. Community XP appears on the Nalanda page.

---

## 5. Build tab — Creator vs QA Hunter

Same page layout; sections show or hide by avatar.

### Creator sees

- **Original requirement** — purpose / change requests  
- **Automation coverage** — yPAD explorer (Plans, Actions, **Designs with D1–D9 persona columns**, ENV)  
- **QA Hunter user stories** — manual scenarios for hunters  
- **QA Hunter team** — roster + **Invite QA Hunter**  
- **Refine with AI** — chat, connectors (JIRA, GitHub, Figma…), budget slider  

### QA Hunter sees

- **Original requirement** (read-only context)  
- **QA Hunter workspace** — Creator chat (read-only), context chips, **Join as QA Hunter**, deliverables form  
- **Automation coverage** — yPAD read-only (no Edit CSV)  
- No budget block, no invite form (Creator-only)  

### Add a challenge

If no suite exists: **Build** empty state → **Add challenge to arena** → scaffolds `y/<name>/` with suite JSON, **D1–D9 persona y3Designs**, starter smoke plans/actions, and `f/fStart/<name>.json`.

### Creator workflow — test data in yDesigns (every new app)

1. **Build** — enter launch prompt + app URL → **Add challenge** (scaffolds yPAD with persona columns).
2. **Designs** — open yPAD **Y Designs** tab; fill `base_url`, route URLs, and per-persona `login_email` / `login_password` / expected values. Column headers show persona names (e.g. Alex Chen (D1)).
3. **Plans / Actions** — add or AI-assist smoke plans; reference `DataName` tokens in actions — never hard-code URLs in y2Actions.
4. **Run** — FoXYiZ via `f/fStart/<suite>.json` (Arena profiles for Smoke/UI/API).
5. **QA Hunter** — record screen in Build → log findings → **Submit QA Hunter report** → Creator reviews hunt artifacts on **BRAHL** for Go/No-Go.

Use Designs tab filters (**URLs**, **Locators**, **Expected**, **Credentials**) and **Active profile only** when editing one persona column.

---

## 6. Projects & folders (FoXYiZ layout)

| Path | Contents |
|------|----------|
| `y/<suite>/` | y1Plans, y2Actions, y3Designs, `<suite>.json` |
| `f/fStart/<suite>.json` | One run config per suite (see `f/fStart_SCOPE.md`) |
| `z/<timestamp>_<suite>/` | Run results, dashboards, BRAHL reports |
| `qoa_web/data/projects.json` | Workspace metadata (chat, budget, QA Hunter roster) |

Selecting **challenge** in the top bar scopes Run, Analyze, Heal, Loop, and BRAHL to that suite.

---

## 7. QA Hunter flow (arena)

1. Creator sets budget with a **QA Hunter %** slice.  
2. Creator **Invite QA Hunter** (optional tag, bug-bounty note).  
3. QA Hunter (H avatar) selects same challenge in top bar → **Join as QA Hunter**.  
4. QA Hunter runs manual tests / FoXYiZ offline → **Record hunt** (screen/audio, findings) → **Submit QA Hunter report** (issues, hours, file upload). Recordings persist across page refresh (IndexedDB) until submit.  
5. Hunt markdown + `.webm` recordings appear on **BRAHL** tab under *QA Hunter* with in-app playback.  
6. **$** tab → QA Hunter wallet shows earnings by challenge.

---

## 8. AI in the app

| Feature | When AI is on |
|---------|----------------|
| Build chat | Scripted + OpenAI assistant (if `OPENAI_API_KEY` set) |
| Analyze | **AI root-cause analysis** on selected run |
| Heal | **AI heal suggestions** |
| BRAHL tab | Chat scoped to project + selected report |
| **.md** button | View docs loaded into AI prompt (BRAHL_PROMPT.md, FoXYiZ.md, this guide) |

**AI off** (manual mode): purpose textarea, QA Hunter runs FoXYiZ locally and uploads Automation + AI reports. Default for **P5**.

---

## 9. Cost meter ($ tab)

**Membership:** ~**$5/mo** for every member.

**Creator QA wallet:** fund from **$50+** per challenge. **QAonAIR retains 5%**; remainder splits across **AI cost**, **human payouts** (QA Hunters), and **admin/ops**.

**Earn credits:** any avatar — **QA Hunting** (join challenges, BRAHL reports) or **Nalanda community** (teach, discuss, invite).

**Payouts:** cash out at **$100+** wallet balance, or apply credits to QA-hunt your own creations.

**Cost meter visibility:** the Build-tab teaser and the **$** tab appear whenever a project is selected. With no budget set, they show a hint to set a budget on the **$** tab rather than hiding — so tracking is always discoverable.

**Creator view:** budget vs spend by BRAHL phase — local vs cloud runtime toggle.  
**QA Hunter view:** wallet, earnings by project, progress to $100 payout threshold.  
**Networker (internal key `networker`):** see **Nalanda** section below — community XP, not paid BRAHL arena.

The **$** tab loads **`GET /api/pricing`** and renders **Pricing & wallet rules** (membership, min wallet, platform fee, payout threshold). Wallet meter shows payout progress when balance is tracked.

Philosophy: minimize cloud/AI cost; maximize local FoXYiZ + human craft.

---

## 9b. Nalanda — free knowledge community

**Nalanda** is the third corner of the arena: learn, teach, discuss, and invite — knowledge is free; paid BRAHL challenges stay on Creator / QA Hunter avatars.

| Section | What you do |
|---------|-------------|
| **Learn** | Featured paths ([Nalanda SkillFlow AI](https://nalanda.base44.app/), [ITelearn](https://itelearn.com/)), community lessons from API, FAQ chips |
| **Teach** | Post lesson title, URL, blurb — `POST /api/nalanda/lessons` |
| **Discuss** | Threads and replies — `GET/POST /api/nalanda/threads` |
| **Invite** | Personal community link — `GET /api/nalanda/invite?profile_id=…` — friends redeem on `/welcome` for 7-day trial |

Community contribution earns **XP** (lessons, shares, replies). Data persists in `data/nalanda.json`.

**Progress dots** under the main tabs show Build → BRAHL completion for Creator/QA Hunter projects only.

---

## 9c. Reporting, zDash & secrets

- **Consistent counts:** Run list, Analyze, and BRAHL all show **plan-level** pass/fail/total (shared `GET /api/runs/{run}/stats`). Failures can never exceed total plans.
- **zDash:** "View zDash" opens the run's actual dashboard file (e.g. `qoa_web_verify_gate_zDash.html`); the link is hidden until the dashboard exists.
- **Loop recovery:** cycle history shows pass/fail per step and a **Recovered** badge when Loop/Verify drives failures to zero; the BRAHL report includes a **Recovery trace**.
- **Secrets / ENV:** the yPAD **ENV** panel is **reference only**. Never enter secrets in the browser — copy keys into `f/.env` (or host environment) on the machine running FoXYiZ.

**Roadmap — storage:** profile and project selection currently persist in browser `localStorage`. A future server-side store (per-user DB) is planned so state follows the account across devices; no DB migration is included today.

---

## 10. About & Admin

- **About** (`/about`) — QA on Air arena, FoXYiZ, Creator/QA Hunter stories, FAQ, vision.  
- **Admin** (`/admin`) — ecosystem stats + **GTM invite batches** (50 Creator / 50 QA Hunter codes). **P6** lands here after sign-in.

---

## 11. Running locally

### Prerequisites

- Python 3.10+ with `pip install -r qoa_web/api/requirements.txt`
- Edge or Chrome (FoXYiZ default: Edge)
- FoXYiZ deps: `pip install -r f/requirements.txt`

### Start

```powershell
cd KK
python qoa_web/run_local.py
# → http://127.0.0.1:8765
```

Hard-refresh (Ctrl+Shift+R) after code changes.

**Verify UI + API with FoXYiZ** (server must be running):

```powershell
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
```

Expect **24/24** Smoke plans · dashboard in `z/<timestamp>_qoa_web_live/`. Or use Arena → Smoke profile → Run.

Before verify: `python FoXYiZ/pyUtils/reset_demo_data.py` (clears join/submit state from prior runs).

### Troubleshooting

| Issue | Fix |
|-------|-----|
| Port 8765 in use | Stop old `run_local.py` process, restart |
| Stale UI / 404 on new API routes | Restart server; hard-refresh browser |
| Verify failures | Check `z/_errors.csv`; restart server |
| Avatar gate in tests | Use `/?reset=1` (see `fresh_url` in yPAD) |

### Regenerate persona yPAD & sign-in profiles

Source of truth: `Docs/test-user-data/*.json` — do not edit `profiles.js` by hand.

```powershell
python u/sync_personas.py
```

### Keep workspace small

```powershell
python u/cleaner.py --apply    # archives z/ brahl_*, dated runs → archive/cleanup/
```

### MCP for Cursor agents

```powershell
python qoa_web/mcp/server.py
```

Requires qoa_web server running on :8765.

---

## 12. Helpful API routes (for AI & integrators)

| Route | Purpose |
|-------|---------|
| `GET /api/health` | Server up |
| `GET /api/suites` | List `y/` projects |
| `GET /api/test-users` | Fictional personas index |
| `GET /api/test-users/{id}` | Persona tasks + sample_data |
| `GET /api/projects?role=client\|consultant` | Workspace projects |
| `POST /api/projects/{id}/chat` | Build chat message + assistant reply |
| `POST /api/projects/{id}/context` | Add connector / URL / note |
| `PATCH /api/projects/{id}` | Budget, name, purpose |
| `POST /api/projects/{id}/join-hitl` | QA Hunter joins project |
| `POST /api/projects/{id}/submit-hitl-report` | QA Hunter report + deliverables |
| `POST /api/projects/{id}/brahl/chat` | BRAHL model Q&A — project + report scoped |
| `GET /api/projects/{id}/brahl/reports` | List reports (automation, QA Hunter, hybrid) |
| `GET /api/projects/{id}/brahl/reports/{run}/content` | Report markdown |
| `POST /api/projects/{id}/brahl/reports` | Link a Verify run to project |
| `GET /api/ai/docs` | Shared `.md` context list |
| `GET /api/projects/{id}/cost-meter` | Budget meter |
| `GET /api/pricing` | Membership, wallet min, fees, payout rules |
| `POST /api/invites/redeem` | Redeem invite code → start trial |
| `GET /api/admin/invites` | GTM batch stats (admin token) |

### BRAHL tab report sources

| Source type | Meaning |
|-------------|---------|
| Automation | FoXYiZ Verify, no human |
| Automation + AI | BRAHL model assisted runs |
| QA Hunter | QA Hunter-enriched report |
| QA Hunter + AI / QA Hunter + Automation | Hybrid deliverables |

---

## 13. Glossary

| Term | Meaning |
|------|---------|
| **BRAHL** | Build · Run · Analyze · Heal · Loop — testing lifecycle |
| **FoXYiZ** | Low-code engine: f(x,y)=z |
| **yPAD** | y1Plans + y2Actions + y3Designs (+ ENV) |
| **QA Hunter** | Problem-solver role (avatar **H**) — joins challenges, submits BRAHL reports |
| **Creator** | Challenge-poster role (avatar **C**) — posts apps to the arena |
| **Persona** | Test profile P1–P9 (not production auth) |
| **Suite** | Named folder under `y/` (e.g. `qoa_web`, `ivvu`) |
| **Verify** | Full FoXYiZ run used for green/red BRAHL reports |

---

## 14. For AI assistants

When helping a user in **qoa_web**:

1. **Ask which persona** (P1–P9) and **avatar** (C, H, or N) — tasks differ. Use `GET /api/test-users/{id}/tasks?avatar=…`.  
2. **Challenge scope** — almost everything requires top-bar challenge selected.  
3. **Unified UX** — never assume a separate QA Hunter layout; same top bar and tabs.  
4. **Source of truth for test users** — `Docs/test-user-data/*.json`, not hard-coded in `profiles.js` (generated).  
5. **In-app AI context** — prefer `.md` docs: BRAHL_PROMPT.md, FoXYiZ.md, **this file**, test-user-data README.
6. **Do not treat personas as real people** — all fictional emails and companies.

Related docs: [Docs/README.md](../Docs/README.md) (handoff hub) · [Docs/HANDOFF.md](../Docs/HANDOFF.md) (export bundle) · [Docs/BRAHL.md](../Docs/BRAHL.md) · [Docs/test-user-data/README.md](../Docs/test-user-data/README.md) · [MEMORY.md](./MEMORY.md) (agents)

---

*BRAHL Web — qoa_web · fictional test data only · local development*
