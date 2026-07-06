# qoa_web Changelog

## 1.3.0 — 2026-07-05

**Invite GTM + leaner UX**

### Features
- **Invite landing** (`/welcome`) — 7-day trial, batch codes, admin GTM panel
- **Routing:** `/` → welcome · `/app` → arena · invite gate on signin/app
- **Persona badge** — compact dismissible strip (Tips / ×) replaces full task list
- **Sign-in** — waitlist form removed; persona grid first; compact cards with More…
- **Pricing tab** — `GET /api/pricing` + wallet rules panel on `$`
- **Parallel batch dashboard** — `u/zBatchDash.py` → `z/zDash_batch_<name>.html`
- Verify: **49/49** (2 sign-in pitch plans disabled; waitlist UI plan replaced)

### Removed / deprecated
- Waitlist form on `/signin` (API retained for legacy; not in verify gate)
- `LAUNCH.md`, `AVATARS_AND_BUILD.md` — merged into qoa_userDoc
- Duplicate `fStart_qoa_web_regression_api.json`, stale demo bundles in `archive/`

## 1.2.0 — 2026-07-05

**Hybrid MVP — demo + waitlist + launch hardening**

### Features
- Waitlist API (`POST /api/waitlist`) + sign-in / about UI
- Admin waitlist count on `/admin` + CSV export (`QOA_ADMIN_TOKEN`)
- Demo banner on app + sign-in (personas vs early access)
- yPAD verify: version launch, hunt evidence, P9 modal, admin, waitlist (+7 plans → **52** total)
- Deploy: `u/export_demo_bundle.py`, `u/patch_ypad_urls.py`, `Dockerfile`, nginx sample
- `f/fStart_qoa_web_smoke_prod.json` post-deploy gate
- [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md) 10-minute team walkthrough

## 1.1.0 — 2026-07-03

**UX polish — dedupe, modals, single version source**

### Changes
- Phase progress bar: dot track only (labels live in phase nav — no duplicate text)
- Click progress dots to jump phases
- Link verify run + HITL submit: modal with run picker (no `prompt()`)
- Footer version from `/api/version` (single `APP_VERSION` in API)
- Post-run quick actions: Open Analyze · View zDash
- Docs: canonical status in `MEMORY.md`; Summary trimmed

## 1.0.0 — 2026-07-03

**Local BRAHL web — production-ready desktop release**

### Features
- Full six-phase BRAHL UI: Build, Run, Analyze, Heal, Loop, BRAHL
- Client vs HITL avatars with project-scoped context
- Add project modal, build checklist, locked-phase CTAs, role-switch modal
- Context strip (status + project meta), consultant filter/sort/compact mode
- Phase progress indicator across the BRAHL cycle
- Run: suite picker + fStart config + live job log
- Analyze: run list, failures table, zDash link
- Heal: shrink to failures / restore Run=Y (BRAHL.py parity)
- Loop: Step 0, Loop 1/2/3, Verify with auto shrink/restore, cycle history, report generate
- BRAHL tab: report list, viewer, model chat, link verify run
- REST API including `/api/version`, `/api/ypad/shrink`, `/api/ypad/restore`, cycle history
- FoXYiZ verify suite: 60 plans (Client + HITL)

### v1.0.1 — dual avatar verify

- HITL reuse plan `PReuse_qoa_web_HitlReady`
- 10 HITL-specific UI/API plans (Run, Analyze, Heal, Loop, BRAHL scoped)
- Consultant auto-select first project on gate entry
- **60/60** FoXYiZ verify · see qoa_userDoc launch section

## 0.5 — 2026-07-03
- Context strip, consultant toolbar, mobile topbar polish

## 0.4 — 2026-07-03
- Add project modal, checklist, locked CTAs, role-switch modal

## 0.3 — 2026-07-03
- Six phases, avatars, project scope, BRAHL reports tab
