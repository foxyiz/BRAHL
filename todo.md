# BRAHL — go-live checklist (prod)

**Local resume (BRAHL / Arena / fStart):** use **[NEXT.md](NEXT.md)** — not this file.

**Prod:** https://brahl.qaonair.com · **Repo:** https://github.com/foxyiz/BRAHL (`main`) · deploy ~6h after push  
**Local:** http://127.0.0.1:8765 · Spelling: **BRAHL** · **FoXYiZ**

Guests can use BRAHL without login (`/app?demo=1`). Turn that off only after Google auth works.

---

## 1. Ship code to brahl

- [ ] Push / merge latest KK → GitHub `main`
- [ ] Wait for sync (~6h), then check `https://brahl.qaonair.com/api/health`
- [ ] Spot-check: welcome, `/pricing`, `/app?demo=1`, Admin open

## 2. Host env (web box)

Set these on the server (never commit real secrets):

- [ ] `APP_BASE_URL=https://brahl.qaonair.com`
- [ ] `JWT_SECRET=` (strong random value)
- [ ] `OPENAI_API_KEY=` (or keep BYOK on Creator machines)
- [ ] Until auth is live: `QOA_ALLOW_DEMO=1`, `QOA_AUTH_REQUIRED=0`, `QOA_ADMIN_OPEN=1`

## 3. Authentication (Google)

- [ ] Create Google OAuth app → set redirect: `https://brahl.qaonair.com/api/auth/google/callback`
- [ ] Put `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` on the host
- [ ] Test Sign in / Sign up → lands in BRAHL with a real account
- [ ] Then lock testing mode: `QOA_ALLOW_DEMO=0`, `QOA_AUTH_REQUIRED=1`, `QOA_ADMIN_OPEN=0`

## 4. Payments (Stripe)

**Code is ready** (Checkout, webhooks, wallet apply, Customer Portal, pending claim). You only need host keys.

- [ ] Stripe account + products/prices (Hunter $5 / $20 / $50, Creator wallet $50+)
- [ ] Host: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, optional `STRIPE_PRICE_MEMBERSHIP`
- [ ] Enable **Customer portal** in Stripe Dashboard (cancel / payment method / invoices)
- [ ] Webhook → `https://brahl.qaonair.com/api/billing/webhook`
  - Events: `checkout.session.completed`, `checkout.session.async_payment_succeeded`,
    `customer.subscription.updated`, `customer.subscription.deleted`
- [ ] Test while signed in: subscribe, top up, apply portable wallet → project, Manage subscription
  - Hunter AI → `users` membership fields (+ period end)
  - Creator top-up → `creator_wallet_usd` or selected project `budget_usd`
  - Ledger: `qoa_web/data/billing_ledger.json`

## 5. Cloud Run (FoXYiZ on AWS)

Without this, Run/Loop on the website won’t use the team EC2 worker.

- [ ] Document how Arena starts/polls a job on EC2
- [ ] Wire `runtime_mode: cloud` → team AWS EC2 (`FOXYIZ_HEADLESS=true`)
- [ ] Confirm live suites run from brahl.qaonair.com (Math / nalanda_app / qoa_web_live)

## 6. Before calling it “live”

- [ ] Rotate any OpenAI key that was ever pasted in chat
- [ ] Smoke: health, guest→auth path, Stripe test charge, one cloud Run
- [ ] Invites / waitlist ready if you want gated access (optional)

---

## Later (not blocking first go-live)

- [ ] Hosted AI quotas (`QOA_AI_HOSTED=1`) if platform pays for OpenAI
- [ ] Strategy/plan.md save under `y/<suite>/`
- [ ] Richer Creator admin (cost / AI) in Arena
- [ ] Dockerfile path cleanup (only if someone still builds the image)

## Already done (don’t redo)

Landing, pricing page, guest/demo testing mode, Google OAuth code path, signup/login UI, mobile polish, Admin open-for-test, Stripe Checkout + webhook entitlements (keys on host), Heal Apply, live Run console, deploy docs.
