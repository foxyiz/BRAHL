# Deploy — brahl.qaonair.com

Primary ship path is **GitHub → [brahl.qaonair.com](https://brahl.qaonair.com)** every ~6 hours.  
FoXYiZ cloud execution runs on **team AWS EC2**. Docker / DIY VPS is optional only.

## Pipeline

| Piece | Where |
|-------|--------|
| Source | [github.com/foxyiz/BRAHL](https://github.com/foxyiz/BRAHL) · branch **`main`** (mirrors KK: `FoXYiZ/`, `qoa_web/`, `Docs/`) |
| Web / Arena | Auto-sync → **https://brahl.qaonair.com** (~6h) |
| FoXYiZ engine (cloud) | **AWS EC2** worker — Arena `runtime_mode: cloud` (wire-up still in progress) |
| FoXYiZ engine (desktop) | Creator machine — `runtime_mode: desktop` / local Run |
| Docker | Optional alternate host only — not required for qaonair |

```text
KK/ → push main → GitHub BRAHL → (~6h) → brahl.qaonair.com Arena
                                              └─ Run cloud → EC2 FoXYiZ
                                              └─ Run local → desktop FoXYiZ
```

## Repo layout (do not flatten)

| Path | Role |
|------|------|
| `qoa_web/` | Arena UI + FastAPI |
| `FoXYiZ/f|x|y|z|pyUtils` | Engine — **not** root-level `f/` anymore |
| `FoXYiZ/f/.env` | Secrets on host only (`OPENAI_API_KEY`, …) — never git |
| `Docs/` | Slim reference |

## Host env (web box)

| Variable | Purpose |
|----------|---------|
| `APP_BASE_URL` | `https://brahl.qaonair.com` |
| `JWT_SECRET` | Auth signing |
| `QOA_ADMIN_OPEN` | `1` while testing Admin without login; `0` when accounts linked |
| `QOA_ALLOW_DEMO` | As agreed for `/app?demo=1` |
| `OPENAI_API_KEY` | Optional AI — prefer `FoXYiZ/f/.env` or host secret |
| `QOA_AI_HOSTED` | Optional platform-key mode |
| `STRIPE_SECRET_KEY` | Optional — enables `/pricing` Checkout (`sk_…`) |
| `STRIPE_WEBHOOK_SECRET` | Optional — verifies `/api/billing/webhook` |
| `STRIPE_PRICE_MEMBERSHIP` | Optional Stripe Price id for ~$5/mo membership |
| `FOXYIZ_HEADLESS` | `true` on servers / EC2 |

## After each sync — smoke

| Check | Pass |
|-------|------|
| `https://brahl.qaonair.com/api/health` → 200 | |
| `/admin` opens (testing: `admin_open: true`) | |
| Signup / JWT → `/app` | |
| Build: purpose, BRAHL Plan, yPAD dock | |
| Run console streams while FoXYiZ runs (desktop) | |
| Spelling **BRAHL** / **FoXYiZ** | |

Patch suite base URLs when verifying against the live host:

```powershell
$env:APP_BASE_URL = "https://brahl.qaonair.com"
# use team patch script if present, e.g. u/patch_ypad_urls.py
```

## EC2 contract (cloud Run)

Arena should start/poll FoXYiZ jobs on EC2 (not only desktop). Document the real team hook here as it lands:

| Concern | Decision (fill in) |
|---------|-------------------|
| How Arena starts a job | queue URL / SSM / SSH / HTTP worker API |
| Auth between web ↔ EC2 | |
| Config + suite sync on EC2 | same `main` tree; lean suites: `Math`, `nalanda_app`, `qoa_web_live` |
| Headless | `FOXYIZ_HEADLESS=true` |
| Result path | `FoXYiZ/z/<run>/` visible to API or copied back |

Until wired: use **desktop** Run on Creator machines; web UI still deploys via GitHub sync.

## Optional: Docker / Bluehost VPS

Not the primary path. If needed: `qoa_web/docker-compose.yml`, [qoa_web/DEPLOY.md](../qoa_web/DEPLOY.md). Shared PHP hosting will not work (need always-on Python + writable `data/`).

## Local

```powershell
cd KK
pip install -r qoa_web/api/requirements.txt
# optional: OPENAI_API_KEY in FoXYiZ/f/.env
python qoa_web/run_local.py
# Arena: http://127.0.0.1:8765/app?demo=1
```
