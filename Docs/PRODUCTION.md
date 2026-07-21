# Production runbook — brahl.qaonair.com

Canonical host: **https://brahl.qaonair.com** (QAonAir / qaonair.com).  
Spellings: **BRAHL** · **FoXYiZ**. See [terminology.md](./terminology.md).

This runbook implements the launch plan (ship → env → Google → Stripe → EC2 → gate).

---

## 1. Ship

```powershell
cd c:\006\FXYZ\KK
python FoXYiZ\pyUtils\cleaner.py --apply --ypad-versions
# commit + push main → https://github.com/foxyiz/BRAHL
```

After sync (~6h or team trigger):

```powershell
Invoke-RestMethod https://brahl.qaonair.com/api/health
# Expect status=ok + readiness object
```

Spot-check: `/welcome` · `/pricing` · `/app?demo=1` (until auth locked) · `/admin`

---

## 2. Host env

Copy [qoa_web/.env.production.example](../qoa_web/.env.production.example) on the server. Minimum:

| Variable | Prod |
|----------|------|
| `APP_BASE_URL` | `https://brahl.qaonair.com` |
| `JWT_SECRET` | strong random (not the dev default) |
| `QOA_ALLOW_DEMO` | `1` until Google works, then `0` |
| `QOA_AUTH_REQUIRED` | `0` → `1` after Google |
| `QOA_ADMIN_OPEN` | `1` → `0` after real admins |
| `FOXYIZ_HEADLESS` | `true` on workers |

Validate on the host:

```powershell
python qoa_web/scripts/prod_readiness.py
```

---

## 3. Google OAuth

1. Google Cloud Console → OAuth client (Web).
2. Authorized redirect: `https://brahl.qaonair.com/api/auth/google/callback`
3. Set `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` on host.
4. Test Sign in → `/app` with a real account.
5. Lock: `QOA_ALLOW_DEMO=0`, `QOA_AUTH_REQUIRED=1`, `QOA_ADMIN_OPEN=0`.

Code path: [qoa_web/api/auth.py](../qoa_web/api/auth.py). Health shows `readiness.google_oauth_configured`.

---

## 4. Stripe

1. Stripe products / prices (Hunter $5/$20/$50, Creator wallet).
2. Host: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_MEMBERSHIP`.
3. Webhook: `https://brahl.qaonair.com/api/billing/webhook`
4. Test Checkout from `/pricing`.

Code: [qoa_web/api/billing.py](../qoa_web/api/billing.py). Health: `readiness.stripe_configured`.

---

## 5. Cloud FoXYiZ (EC2)

| Concern | Decision |
|---------|----------|
| How Arena starts a job | HTTP POST to `FOXYIZ_CLOUD_WORKER_URL/v1/jobs` |
| Auth web ↔ EC2 | `Authorization: Bearer FOXYIZ_CLOUD_TOKEN` |
| Config + suite sync | Same `main` tree on EC2 (`FoXYiZ/` + lean fStarts) |
| Headless | `FOXYIZ_HEADLESS=true` on worker |
| Result path | Worker returns job status/`output_dir`; Arena polls `/v1/jobs/{id}` |

**On EC2:**

```bash
export FOXYIZ_HEADLESS=true
export FOXYIZ_CLOUD_TOKEN=shared-secret
python FoXYiZ/pyUtils/cloud_worker_server.py --host 0.0.0.0 --port 8770
# open security group :8770 to Arena host only
```

**On Arena host:**

```bash
export FOXYIZ_CLOUD_WORKER_URL=https://ec2-host:8770
export FOXYIZ_CLOUD_TOKEN=shared-secret
```

In Arena Cost tab set project **runtime_mode = cloud**. Run uses that mode automatically.

Client: [qoa_web/api/cloud_worker.py](../qoa_web/api/cloud_worker.py) · Server: [FoXYiZ/pyUtils/cloud_worker_server.py](../FoXYiZ/pyUtils/cloud_worker_server.py)

Until the worker URL is set, cloud mode fails loudly; desktop/local Run still works.

---

## 6. Go-live gate

| Check | Pass |
|-------|------|
| `/api/health` readiness | jwt + google (when locking) + optional stripe/cloud |
| `qoa_web_live` Smoke | green (desktop or cloud) — against brahl: `python qoa_web/scripts/patch_live_urls.py` then smoke; restore with `--base http://127.0.0.1:8765` |
| Guest→Google | works |
| Stripe test charge | works (or documented deferred) |
| Backup | `python qoa_web/scripts/backup_data.py` on a schedule |

---

## Apex qaonair.com

Marketing/landing may live on apex; product Arena is **brahl.qaonair.com**. Point apex CTA to `/welcome` or brahl subdomain.
