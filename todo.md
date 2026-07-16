# BRAHL — what’s next (go live)

**Prod:** https://brahl.qaonair.com · **Repo:** https://github.com/foxyiz/BRAHL (`main`) · deploy ~6h after push  
**Local:** http://127.0.0.1:8765 · Spelling: **BRAHL** · **FoXYiZ**

Right now guests can use BRAHL without login (`/app?demo=1`). Turn that off only after Google auth works.

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

Pricing UI is ready; charges need live Stripe wiring.

- [ ] Stripe account + products/prices (Hunter $5 / $20 / $50, Creator wallet $50+)
- [ ] Host: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` as needed
- [ ] Webhook → `https://brahl.qaonair.com/api/billing/webhook`
- [ ] Test Checkout end-to-end; confirm wallet / membership updates after pay

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

Landing, pricing page, guest/demo testing mode, Google OAuth code path, signup/login UI, mobile polish, Admin open-for-test, Stripe scaffold, Heal Apply, live Run console, deploy docs.
