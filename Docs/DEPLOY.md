# Deploy — Bluehost / VPS (+ future AWS)

Ship **qoa_web** (FastAPI + static web) with optional **FoXYiZ** for server-side Run/Verify.  
Deep host notes retired to `archive/docs-retired-20260714/Bluehost.md` and `aws.md`.

## Bundle (slim)

| Include | Skip |
|---------|------|
| `qoa_web/` (api, web, data writable) | `archive/`, `FoXYiZ/z/` history |
| `FoXYiZ/f|x|y` (lean suites: Math, nalanda_app, gate suites as needed) | Fat journey CSVs unless you need them |
| `FoXYiZ/f/.env` secrets on the server only | Real keys in git |

Also see [qoa_web/DEPLOY.md](../qoa_web/DEPLOY.md) · Docker: `qoa_web/docker-compose.yml`.

## Bluehost / VPS

- **Shared PHP hosting:** no — need always-on Python + writable `data/`.
- **VPS / Cloud:** yes — Python 3.11+, nginx reverse-proxy to uvicorn `:8765`, HTTPS.
- Engine on server: `FOXYIZ_HEADLESS=true`.

```powershell
# From KK/ on the VPS
pip install -r qoa_web/api/requirements.txt
# set QOA_ALLOW_DEMO=0 in production env
python qoa_web/run_local.py
```

## Launch smoke checklist

| Check | Pass |
|-------|------|
| `/api/health` → 200 | |
| `QOA_ALLOW_DEMO=0` → `/api/config` `allow_demo: false` | |
| Signup / login / JWT → `/app` | |
| Project ownership: User A cannot read User B's owned project | |
| Build: BRAHL Plan generate + accept; Tests / Steps / Test data | |
| yPAD dock + Wallet dock visible with a project | |
| Run mentions FoXYiZ only; spelling **BRAHL** / **FoXYiZ** | |
| Optional: `pytest qoa_web/api/test_runner_stats.py qoa_web/api/test_auth.py -q` | |

## AWS (later)

Same engine layout on EC2/ECS with headless Chrome; Arena already has `runtime_mode: local|cloud` metering hooks. Full design: `archive/docs-retired-20260714/aws.md`.
