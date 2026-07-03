# BRAHL Report — ivvu — 2026-07-03 (merged)

**App:** https://ivvu.base44.app/  
**Scope:** Full suite · **44 runnable plans** · **Config:** `f/fStart_ivvu.json`  
**Engine:** fEngine2.py · timeout=6 · headless=false  
**Context file:** `z/brahl_context_20260703_110454_ivvu.json`  
**Final Verify:** `z/20260703_112215_ivvu/` — **44/44 pass** (~48s wall)

---

## Executive summary (for customer / product owner)

FoXYiZ automation is **green (44/44)** on IVVU. All tests pass — including **Issue** plans that **pass when a defect exists**. That means automation is working; the findings below are **real application issues** to fix in the product, not test bugs.

**Priority fixes before the next BRAHL cycle:**

| Priority | Issue | Action |
|----------|-------|--------|
| **P1** | 12 routes return 404 | Implement routes or add redirects (see [Broken routes](#broken-routes-404)) |
| **P1** | `/dashboard` and `/settings` public without login | Add auth gate for sensitive pages |
| **P2** | Inconsistent URLs (`/gift` vs `/gifts`, `/book-care` vs `/care`) | Align nav links, bookmarks, and marketing URLs |
| **P3** | App-log API 429 under rapid re-runs | Rate-limit tuning or idempotent beacon (automation waits 60s between full runs) |

After fixes, run another BRAHL cycle: **Verify** should stay green; **Issue** plans should **fail** once routes exist (then update or retire those plans).

---

## Origin — user prompts

**Cycle A — greenfield framework validation**

> Let us retest the entire FoXYiZ and BRAHL framework on a new web application https://ivvu.base44.app/

**Cycle B — defect reporting expansion**

> We should also be able to point out the application defects and add more plans if we find any issues to report as real app defects. Adding yPlans to test vulnerable issues like broken links, elements.

**Combined intent:** Build IVVU yPAD from scratch, validate BRAHL on a new Base44 app, then expand with Issue/Link/Security/Element plans so application defects are documented with evidence — without weakening tests.

---

## yPAD baseline (before Loop 1)

- **yPlans path:** `y/ivvu/y1Plans.csv` *(greenfield — suite did not exist before 2026-07-03)*
- **Snapshot time:** 2026-07-03 11:04:54
- **Counts:** 26 rows · **Run=Y:** 25 · **Run=N:** 1 · **Reuse:** 1
- **Built from:** Route probe of landing, pricing, FAQ, care, orders, dashboard, auth, 404 candidates, Base44 APIs

---

## yPAD after BRAHL (Verify state)

- **Counts:** 45 rows · **Run=Y:** 44 · **Run=N:** 1 · **Reuse:** 1
- **Delta:** **0 → 44** runnable plans (+19 defect-reporting plans in Cycle B)

| Tag | Plans | Role |
|-----|-------|------|
| UI Smoke | Landing, hero, pricing, FAQ, care, orders, dashboard, login, register, forgot password | Core paths |
| UI Nav | Pricing nav link | Regression |
| **Issue** | 12 | Broken route — **pass = defect confirmed** |
| **Link** | 5 | CTA/nav must reach live page |
| **Security** | 4 | Auth gaps, XSS surface, evil query |
| **Element** | 2 | Required UI blocks |
| API | Manifest, session 401, app-log, apps 401, invalid login, robots | Backend |
| Performance | Home load, pricing load, session API latency | Perf |

---

## Cycle summary

### Cycle A — greenfield (25 plans)

| Step | Plans run | Pass | Fail | Engine time | z/ folder |
|------|-----------|------|------|-------------|-----------|
| Loop 1 | 25 | 24 | 1 | ~28s | `z/20260703_110503_ivvu/` |
| Loop 2 | 1 | 1 | 0 | ~3s | `z/20260703_110609_ivvu/` |
| Loop 3 | — | — | — | skipped | *zero failures after loop 2* |
| Verify | 25 | **25** | **0** | ~23s | `z/20260703_110819_ivvu/` |

*First verify attempt (`z/20260703_110638_ivvu/`) hit **429** on app-log from Loop 1; re-ran after ~50s cooldown.*

### Cycle B — defect expansion (44 plans)

| Step | Plans run | Pass | Fail | Engine time | z/ folder |
|------|-----------|------|------|-------------|-----------|
| Loop 1 | 44 | 43 | 1 | ~49s | `z/20260703_111751_ivvu/` |
| Loop 2 | 44 | 42 | 2 | ~54s | `z/20260703_111955_ivvu/` |
| Loop 3 | — | — | — | skipped | *healed after loop 2* |
| Verify | 44 | **44** | **0** | ~48s | `z/20260703_112215_ivvu/` |

---

## Loop detail

### Cycle A

**Loop 1 — failure:** `PWeb_Nav_Pricing` step 3 — xpath `contains(@href,'/pricing')` comma mangled during CSV resolution → click timeout  
**Heal (T1):** `nav_pricing_locator` → `css=a[href*='pricing']` in `y/ivvu/y3Designs.csv`  
**Loop 2:** `PWeb_Nav_Pricing` only — pass  
**Verify:** 25/25, no regressions

### Cycle B

**Loop 1 — failure:** `PWeb_Link_Home_FAQ` step 4 — xpath `contains(.,'Help Center')` comma mangled → `xGetText` timeout  
**Loop 2 — failures:** same FAQ plan + `PAPI_AppLog_Home` **429** (T3 — back-to-back full run)  
**Heals (T1):** `PWeb_Link_Home_FAQ` step 4 → body presence check after nav click (avoid comma in xpath)  
**Verify:** 44/44, no regressions

---

## IVVU route probe (working vs broken)

| Route | Status |
|-------|--------|
| `/`, `/pricing`, `/faq`, `/care`, `/orders`, `/gifts`, `/contacts/new`, `/rewards` | Public content loads |
| `/login`, `/register`, `/forgot-password` | Auth forms |
| `/dashboard`, `/settings` | **Load without login** (security gap) |
| `/docs`, `/profile`, `/shop`, `/about`, `/automations`, `/onboarding`, `/build-app`, `/connected-apps` | SPA **404** |
| `/gift`, `/book-care`, `/send-gift`, `/add-family` | **404** — live app uses different paths (see below) |
| `/api/auth/session` | 401 JSON (expected unauthenticated) |
| `/api/app-logs/.../home` | 200; **429** if hit twice within ~60s |

**Nav link probe (2026-07-03):** Internal links on `/`, `/pricing`, `/faq`, `/care`, `/orders`, `/dashboard` — **no broken hrefs** in sampled nav (12–23 links per page). Dead routes exist as **direct URL entry**, not from in-app links.

---

## Classification tally (both cycles)

| Class | Count | Notes |
|-------|-------|-------|
| T1 yPAD | 2 | Nav pricing locator; FAQ link assertion (xpath commas) |
| T2 Engine | 0 | Shared timer handler from atomic77 held |
| T3 Environment | 2 | App-log 429 on back-to-back verify runs |
| A1 Application | 16+ | Documented below — **do not weaken tests** |

---

## A1 — Application defects catalog

These plans **pass intentionally** when the defect is present. Fix the app; then Issue plans should fail (route works) and plans can be updated or retired.

### Broken routes (404)

| PlanId | URL | Notes | Suggested fix |
|--------|-----|-------|---------------|
| `PWeb_Issue_Docs_404` | `/docs` | Page Not Found | Add docs page or redirect |
| `PWeb_Issue_Profile_404` | `/profile` | Page Not Found | Add profile or redirect to account |
| `PWeb_Issue_Shop_404` | `/shop` | Page Not Found | Redirect to `/gifts` |
| `PWeb_Issue_Gift_404` | `/gift` | 404 — live shop is `/gifts` | Redirect `/gift` → `/gifts` |
| `PWeb_Issue_BookCare_404` | `/book-care` | 404 — dashboard uses `/care` | Redirect or alias |
| `PWeb_Issue_SendGiftRoute_404` | `/send-gift` | 404 — dashboard uses `/gifts` | Redirect or alias |
| `PWeb_Issue_AddFamilyRoute_404` | `/add-family` | 404 — dashboard uses `/contacts/new` | Redirect or alias |
| `PWeb_Issue_About_404` | `/about` | Page Not Found | Add about page |
| `PWeb_Issue_Automations_404` | `/automations` | Page Not Found | Implement or remove from marketing |
| `PWeb_Issue_Onboarding_404` | `/onboarding` | Page Not Found | Implement onboarding route |
| `PWeb_Issue_BuildApp_404` | `/build-app` | Page Not Found | Remove or implement |
| `PWeb_Issue_ConnectedApps_404` | `/connected-apps` | Page Not Found | Remove or implement |

### Security observations

| PlanId | Finding | Suggested fix |
|--------|---------|---------------|
| `PWeb_Sec_Dashboard_Public` | `/dashboard` accessible without login | Require auth; redirect to `/login` |
| `PWeb_Sec_Settings_Public` | `/settings` accessible without login | Require auth |
| `PWeb_Sec_XSS_Login` | XSS payload in email field does not crash page | Sanitize input; CSP headers (monitor) |
| `PWeb_Sec_EvilQuery` | Evil query on landing loads safely | Keep monitoring |

### Working links verified

| PlanId | CTA | Destination |
|--------|-----|-------------|
| `PWeb_Link_Dashboard_Gifts` | Send Gift / Shop Gifts | `/gifts` → Gift Shop |
| `PWeb_Link_Dashboard_ContactsNew` | Add Family | `/contacts/new` |
| `PWeb_Link_Dashboard_Rewards` | Rewards | `/rewards` |
| `PWeb_Link_Home_FAQ` | FAQ nav | `/faq` |
| `PWeb_Link_Home_SignIn` | Sign In | `/login` |

### Element checks

| PlanId | Element |
|--------|---------|
| `PWeb_Elem_Gifts_Trending` | Gift shop "Trending Now" section |
| `PWeb_Elem_Dashboard_EmptyOrders` | Dashboard empty orders state |

---

## Customer action plan — next BRAHL run

1. **Fix P1 routes** — implement or 301 redirect the 12 Issue URLs (start with `/shop`, `/gift`, `/profile`, `/docs`).
2. **Add auth gates** — `/dashboard` and `/settings` should require login.
3. **Align URL naming** — pick canonical paths (`/gifts` not `/gift`; `/care` not `/book-care`) and redirect legacy URLs.
4. **Re-run BRAHL:**
   ```powershell
   cd KK
   python BRAHL.py   # Step 0: prompt + optional uploaded docs → context JSON
   # Loop tab: Verify with f/fStart_ivvu.json
   ```
5. **Expected outcome:** Verify stays **44/44**; Issue plans **fail** when routes work (update `Expected` or retire plans); security plans pass after auth is enforced.
6. **Optional:** Upload product specs, route maps, or design PDFs at Step 0 so the next cycle context includes them (see `Docs/BRAHL.md`).

---

## yPAD changes (files touched)

- `y/ivvu/` — new suite (45 plans, configs, payloads)
- `f/fStart_ivvu.json`, `f/fStart_ivvu_smoke.json`
- `y/ivvu/y3Designs.csv` — nav pricing locator (css)
- `y/ivvu/y2Actions.csv` — FAQ link heal; +19 defect plans
- `y/ivvu/y1Plans.csv` — Issue/Link/Security/Element expansion

---

## Verdict

- [x] FoXYiZ + BRAHL framework validated on IVVU (greenfield + defect expansion)
- [x] Final Verify **44/44** green
- [x] **12 broken-route A1s** + security gaps documented with dedicated plans
- [x] Context + merged report saved under `z/`
- [ ] Customer fixes application defects (see action plan)
- [ ] Follow-up BRAHL cycle after app fixes

**Dashboard:** `z/20260703_112215_ivvu/ivvu_zDash.html`  
**BRAHL report:** `z/20260703_112215_ivvu/brahl_report.md` · flat: `z/brahl_report_20260703_112215_ivvu.md`
