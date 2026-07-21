# PRD — QA on Air (KK monorepo)

**Product:** QA on Air  
**Lifecycle brand:** BRAHL (Build → Run → Analyze → Heal → Loop)  
**Automation engine:** FoXYiZ (`f(x, y) = z`)  
**Primary app:** BRAHL Web / Arena (`qoa_web`)  
**Repo / working tree:** `KK/` (mirrors `github.com/foxyiz/BRAHL`)  
**Local:** `http://127.0.0.1:8765` · **Prod:** `https://brahl.qaonair.com` - not working as AWS integration requires to pay old bills 
**Document status:** Living product PRD — use to rebuild or onboard without chat history  
**Audience:** Creators, engineers, agents, GTM

This PRD describes **the whole KK product**, not a single challenge suite. FoXYiZ is covered as the **engine the application runs on**, not as a standalone product brief.

---

## 1. One-line positioning

**QA on Air** is an invite-oriented P2P quality marketplace where **Creators** post app challenges and fund a QA wallet, **QA Hunters** deliver human evidence, and **BRAHL** + **FoXYiZ** automate Build → Run → Analyze → Heal → Loop to a clear **Go / No-Go** scorecard.

Tagline (product): **You Build, We QA — let's BRAHL!**

---

## 2. Problem

Shipping software without a shared, repeatable quality loop means:

- Creators cannot tell **prod-ready vs not** with one artifact.
- Human QA and automation live in different tools with no common report.
- Cloud-only AI testing burns budget without owning locators, plans, or evidence on disk.
- Hunters have no structured way to get paid for findings tied to a Creator challenge.

---

## 3. Solution

| Layer | What it is | What users see |
|-------|------------|----------------|
| **QA on Air** | Marketplace + ecosystem brand | Creators ↔ Hunters, wallets, invites |
| **BRAHL** | Quality lifecycle name + in-app phases | Build / Run / Analyze / Heal / Loop / BRAHL report |
| **BRAHL Web (Arena)** | Desktop-oriented web app (`qoa_web`) | Browser UI over local or hosted API |
| **FoXYiZ** | LCNC automation engine | Invisible referee on **Run** and **Loop**; yPAD files on disk |

**How the application works using FoXYiZ**

```
Creator shapes challenge in Arena (Build)
        ↓
Arena API launches FoXYiZ fEngine2 with fStart + yPAD (Run / Loop)
        ↓
FoXYiZ writes z/<run>/ (CSV, zDash, errors, brahl_report.md)
        ↓
Arena Analyze / Heal / BRAHL read those artifacts (Heal may edit yPAD)
        ↓
Go / No-Go + hunter evidence + cost meter
```

**Hard rule:** Run and Loop are **FoXYiZ only — never the LLM**. AI (optional BYOK) may assist Build, Analyze, Heal, planner, BRAHL chat, and Atomic 77.

Mental model: **FoXYiZ is the referee; the BRAHL report is the scorecard.**

---

## 4. Goals & non-goals

### Goals

1. One Arena where Creator + Hunter + automation share a challenge.
2. Deterministic automation via open yPAD CSVs (`y/`) and run folders (`z/`).
3. Lifecycle that heals **test debt** (T1–T3) without weakening **app defects** (A1).
4. Optional AI that stays cheap (local FoXYiZ first; BYOK when wanted).
5. Wallet economics: Creator funds QA; Hunters cash out; platform fee is thin.

### Non-goals

- Replacing FoXYiZ with LLM-authored clicks at Run time.
- Owning every customer’s app (challenges point at *their* URLs).
- Shipping a separate Electron binary as the primary client (desktop = local web + FoXYiZ today).
- Putting secrets, `z/` blobs, or `archive/` into agent/product context.

---

## 5. Personas & roles

| UI label | Internal key | Job to be done |
|----------|--------------|----------------|
| **Creator** | `client` | Post challenge, fund wallet, BRAHL to Go/No-Go |
| **QA Hunter** | `consultant` | Hunt bugs, attach evidence, get paid |
| **Nalanda** | `networker` | Learn / teach / discuss — **no** BRAHL phases |
| **Promoter** | `promoter` | Share invite posts; earn referral path |
| **Admin** | admin / P6 | Ecosystem stats, GTM invite batches |

**Arena metaphor:** Creator = Champion · QA Hunter = Contender · FoXYiZ = referee.

Demo personas **P1–P9** (sign-in without password in demo) live under `Docs/test-user-data/` and are synced via `FoXYiZ/pyUtils/sync_personas.py`.

---

## 6. Product surfaces

| Surface | URL | Purpose |
|---------|-----|---------|
| Welcome | `/welcome` | Invite / trial, role entry, AI planner door |
| Sign-in | `/signin` | Demo personas P1–P9 |
| Arena | `/app` (local often `?demo=1`) | Full BRAHL cycle |
| Admin | `/admin` | Ecosystem + invite batches |
| About | `/about` | Story, FAQ, marketplace framing |
| Pricing | `/pricing` | Membership + wallet rules |
| Login / Signup | `/login`, `/signup` | Account path (prod roadmap) |

### Arena phase tabs

| Phase | Purpose | Uses FoXYiZ? | Uses AI? |
|-------|---------|--------------|----------|
| **Build** | Purpose, budget, yPAD, hunters, docs | Reads/writes `y/` via API | Optional assist |
| **Run** | Execute fStart + profiles + threads | **Yes — engine** | **Never** |
| **Analyze** | Inspect `z/`, classify T1–T3 vs A1 | Reads `z/` | Optional RCA |
| **Heal** | Fix yPAD; Shrink/Restore for Loop | Writes `y/` | Optional suggest |
| **Loop** | L1–L3 + Verify schedule | **Yes — engine** | **Never** |
| **BRAHL** | Cycle report, Go/No-Go, evidence, chat | Reads report / `z/` | Optional Q&A |
| **$** | Cost meter, wallet, pricing | — | Metering only |
| **Nalanda** | Community learn/teach | — | FAQ; no BRAHL |

**Atomic 77:** idea-to-launch assistant inside QA on Air (not a substitute for Run).

---

## 7. Architecture (KK)

```
KK/
  FoXYiZ/          Automation engine  f · x · y · z · pyUtils
  qoa_web/         BRAHL Web Arena     web/ + api/ + data/
  Docs/            Product & agent reference
  archive/         Retired — out of product/agent context
  PRD.md           This document
  NEXT.md          Resume todos
  todaysummary.md  Latest session notes
```

### 7.1 FoXYiZ — `f(x, y) = z`

| Letter | Folder | Meaning |
|--------|--------|---------|
| **f** | `FoXYiZ/f/` | Engine (`fEngine2.py`), fStart configs, optional `.env` |
| **x** | `FoXYiZ/x/` | Capabilities / action handlers (UI, API, time, …) |
| **y** | `FoXYiZ/y/<suite>/` | **yPAD** — one folder = one app/challenge |
| **z** | `FoXYiZ/z/` | Run outputs (dashboards, CSV, BRAHL md) |

**yPAD sheets**

| File | Role |
|------|------|
| `y1Plans.csv` | What to run (`PlanId`, `Run`, `Tags`, `DesignId`) |
| `y2Actions.csv` | How (steps, actions, Expected, Critical) |
| `y3Designs.csv` (+ `yD_*`) | Data / locators (persona columns D1…) |
| `<suite>.json` | Suite metadata + `input_files` |

**fStart:** exactly **one** launch JSON per suite — `FoXYiZ/f/fStart/{suite}.json` — with required `capture` block. Arena Run profiles (Smoke → UI → API → Performance → Security → Manual) expand tags; Threads `1` = OR filter; `>1` + multiple profiles = parallel workers. See `FoXYiZ/f/fStart_SCOPE.md`.

### 7.2 Arena → engine path

```
Browser (qoa_web/web)
  → FastAPI (qoa_web/api)
    → FoXYiZ/f/fEngine2.py  (+ fStart, cwd FoXYiZ/)
      → y/<suite>/ yPAD
        → z/<timestamp>_<suite>/
```

API resolves short paths `f/…` `y/…` `z/…` via `FOXYIZ_ROOT`.

### 7.3 BRAHL loop shape (mandatory)

```
Loop 1   full Run=Y → analyze → heal
Loop 2   Run=N on passes → failures only → heal
Loop 3   remaining failures → heal
Verify   restore all Run=Y → full run → BRAHL report
```

**Failure classes:** T1 yPAD · T2 engine/config · T3 environment · **A1 application** (do not “heal away” real product bugs).

---

## 8. “Desktop” vs hosted

| Mode | What it means today |
|------|---------------------|
| **Desktop / local** | `python qoa_web/run_local.py` + browser Arena + FoXYiZ on the Creator machine (`runtime_mode: desktop`) |
| **Hosted** | `https://brahl.qaonair.com` (deploy from `foxyiz/BRAHL` `main`) |
| **Not primary** | Legacy `BRAHL.py` GUI, frozen `Foxyiz2.exe` (historical; exe not in git) |

There is **no separate Electron app** in KK as the shipping client. “Desktop version” = local BRAHL Web over FoXYiZ (open CSVs on disk, Base44-like ease).

**Theme:** Pro is the live skin; Arena fight-ring CSS may remain but runtime forces Pro.

**Demo vs prod**

| | Local / demo | Production |
|--|--------------|------------|
| Host | `127.0.0.1:8765` | `brahl.qaonair.com` |
| Auth | Personas, invite trial, `?demo=1` | JWT / OAuth / Stripe (roadmap) |
| Run | Local FoXYiZ | Local today; cloud EC2 FoXYiZ backlog |
| AI | BYOK in `FoXYiZ/f/.env` | Optional hosted `QOA_AI_HOSTED` |

---

## 9. Marketplace & wallet (high level)

- Membership on the order of **~$5/mo** (see Pricing UI for current copy).
- Creator **QA wallet** from **$50+**; **QAonAIR** retains a thin platform fee (~**5%**); remainder funds AI metering, hunter payouts, ops.
- Hunter cash-out threshold on the order of **$100+** (or credits toward hunting own apps).
- Cost meter (**$** phase) tracks spend by phase; prefer local FoXYiZ over cloud/AI burn.

---

## 10. AI policy

| Allowed | Forbidden |
|---------|-----------|
| Build assist, Analyze RCA, Heal suggestions | Driving **Run** or **Loop** |
| BRAHL chat, Atomic 77, invite planner | Inventing secrets into yPAD |
| BYOK OpenAI (or hosted with caps) | Committing API keys |

Packed skills for agents/AI: `Docs/BRAHL_PROMPT.md` + `Docs/AI_GUARDRAILS.md`. Desktop BYOK: `Docs/BRAHL_DESKTOP_BYOK.md`.

---

## 11. Example challenges (suites)

Shipped under `FoXYiZ/y/` with matching `f/fStart/{suite}.json`:

| Suite | Role |
|-------|------|
| `Math` | Lean day-to-day smoke |
| `nalanda_app` | Lean smoke / UI example |
| `qoa_web` | Arena self-yPAD (journey-capable) |
| `qoa_web_live` | Full Arena UX gate |
| `ultimate_showdown` | External gaming app example |

Each suite is a **challenge**, not the product. New apps = new `y/<suite>/` + fStart + Arena project row.

---

## 12. Functional requirements

### FR-1 Challenge lifecycle
Creator can create/select a challenge bound to a suite, edit yPAD on Build, set wallet, invite hunters, Run profiles, view Analyze, Heal, Loop, and open BRAHL Go/No-Go.

### FR-2 FoXYiZ execution
Arena Run/Loop must invoke `fEngine2` with suite fStart; results land under `z/`; dashboards and BRAHL report remain readable in-app.

### FR-3 yPAD transparency
Live plans/steps/designs visible on Build (CSV table). Optional **snapshots** under `y/<suite>/versions/` are restore points, not a second source of truth.

### FR-4 Hunter path
Manual plans + evidence library + submit deliverables; Creators see evidence on BRAHL.

### FR-5 Role isolation
Nalanda cannot drive BRAHL phases; Creator-only wallet edit; Admin on `/admin`.

### FR-6 Demo
`/app?demo=1` and invite DEMO codes support trial without full prod auth.

### FR-7 Optional AI
When key present, AI features unlock; when absent, scripted/manual paths still work.

---

## 13. Non-functional requirements

| Area | Requirement |
|------|-------------|
| Local boot | Arena up via `run_local.py` on port 8765 |
| Determinism | Same yPAD + env → comparable z results |
| Data ownership | yPAD and z stay on disk / Creator machine in desktop mode |
| Security | No secrets in git; ENV via `.env` / host env |
| Deploy | KK → GitHub `foxyiz/BRAHL` → prod host (see `Docs/DEPLOY.md`) |
| Agent safety | Never load `archive/**` or fat journey CSVs into context |

---

## 14. Rebuild / bootstrap from scratch

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
# optional: set OPENAI_API_KEY in FoXYiZ/f/.env

python qoa_web/run_local.py
# Welcome http://127.0.0.1:8765/welcome
# Arena   http://127.0.0.1:8765/app?demo=1
# Admin   http://127.0.0.1:8765/admin

python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json

python FoXYiZ\pyUtils\reset_demo_data.py   # before clean demo verify
python FoXYiZ\pyUtils\sync_personas.py
```

If port 8765 is taken (WinError 10048), stop the existing `run_local` process first. Restart Arena after API/UI changes; hard-refresh the browser.

**Add a new app challenge**

1. Explore the app (browser / Playwright).
2. Create `FoXYiZ/y/<suite>/` with JSON + y1/y2/y3 + strategy/plan docs.
3. Add `FoXYiZ/f/fStart/<suite>.json` (capture + Smoke tags).
4. Register project in Arena; set wallet ≥ $50.
5. Stabilize Smoke → UI; Manual for hunters; BRAHL on Verify.

---

## 15. Success metrics (product)

| Metric | Signal |
|--------|--------|
| Time to first Smoke green on a new challenge | Hours, not weeks |
| Go/No-Go clarity | Stakeholder can read BRAHL report without opening CSVs |
| Automation share of wallet | Cost meter shows AI vs human vs automation pools |
| Hunter usefulness | Evidence attached to Manual plans / findings |
| Desktop viability | Creator completes a cycle fully offline except app-under-test URL |

---

## 16. Roadmap themes (from NEXT / todo — not commitments)

| Theme | Notes |
|-------|-------|
| Cloud FoXYiZ (EC2) | Run without Creator desktop engine |
| Stripe + OAuth | Real membership and login |
| Invite / GTM scale | Admin batches, promoter loop |
| Heal / Loop polish | Schedules, shrink/restore UX |
| Theme / branding | Keep Pro; arena skin retired at runtime |

Track live todos in `NEXT.md` and `todo.md`.

---

## 17. Out of scope / do not revive in-product

- `KK/archive/**` and `FoXYiZ/f/fStart/archive/**`
- Committing `FoXYiZ/z/**` run blobs
- Waitlist-as-primary (removed from sign-in UX)
- Treating any one suite (Math, Ultimate Showdown, …) as the product itself

---

## 18. Glossary

| Term | Meaning |
|------|---------|
| **QA on Air** | Product / marketplace brand |
| **QAonAIR** | Platform fee / wallet copy spelling |
| **BRAHL** | Lifecycle + report phase |
| **BRAHL Web / Arena** | `qoa_web` application |
| **FoXYiZ** | Automation engine `f(x,y)=z` |
| **yPAD** | Plans + Actions + Designs for a suite |
| **fStart** | Engine launch config per suite |
| **z** | Run output directory |
| **Challenge / suite** | One app under test in `y/<name>/` |
| **Desktop** | Local Arena + FoXYiZ on Creator machine |

---

## 19. Document map (read next)

| Doc | Path |
|-----|------|
| Root README | `README.md` |
| Agent memory | `qoa_web/MEMORY.md` |
| Handoff | `Docs/HANDOFF.md` |
| BRAHL deep dive | `Docs/BRAHL.md` |
| FoXYiZ guide | `FoXYiZ/FoXYiZ_Readme.md` |
| fStart rules | `FoXYiZ/f/fStart_SCOPE.md` |
| End-user guide | `qoa_web/qoa_userDoc.md` |
| Deploy | `Docs/DEPLOY.md` |
| BYOK | `Docs/BRAHL_DESKTOP_BYOK.md` |
| Demo script | `qoa_web/DEMO_SCRIPT.md` |
| Resume | `NEXT.md` · `todaysummary.md` |

---

*End of PRD — QA on Air / KK. Update when marketplace rules, phase UX, or deploy topology change.*
