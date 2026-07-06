# Deploying BRAHL Web for demos

Do **not** upload the entire `KK/` tree (~90 MB with `z/` history) to shared hosting. Ship a **slim demo bundle** instead.

## Quick export

```powershell
cd KK
python u/export_demo_bundle.py --zip
# → archive/demo-bundle/brahl-demo-<timestamp>/
```

Before deploy, patch URLs:

```powershell
$env:APP_BASE_URL = "https://demo.yourdomain.com"
python u/patch_ypad_urls.py
```

## What you need online

| Piece | Purpose |
|-------|---------|
| `qoa_web/api/` | FastAPI backend (Python 3.10+) |
| `qoa_web/web/` | Static UI — welcome, signin, arena, invite gate |
| `qoa_web/data/` | `projects.json`, `invites.json` (writable) |
| `y/qoa_web/` | yPAD for verify |
| `f/fEngine2.py` + `fStart_qoa_web*.json` | Optional: Run tab on server |
| `x/` | FoXYiZ actions (if running verify on server) |

**Skip for demo:** most of `z/`, `archive/`, `.git`, inactive `y/*` suites.

## Docker (recommended VPS)

```bash
cd brahl-demo-<timestamp>
export APP_BASE_URL=https://demo.yourdomain.com
python u/patch_ypad_urls.py
docker build -t brahl-web -f qoa_web/Dockerfile .
docker run -d -p 8765:8765 \
  -e APP_BASE_URL=$APP_BASE_URL \
  -e QOA_ADMIN_TOKEN=your-secret \
  -e FOXYIZ_HEADLESS=true \
  -v brahl-data:/app/qoa_web/data \
  --name brahl brahl-web
```

HTTPS: use [`deploy/nginx.conf.sample`](deploy/nginx.conf.sample) with Let's Encrypt.

## Environment

| Variable | Purpose |
|----------|---------|
| `APP_BASE_URL` | Public URL — run `u/patch_ypad_urls.py` before verify |
| `QOA_ADMIN_TOKEN` | Protects admin invite export + ecosystem endpoints |
| `OPENAI_API_KEY` | Optional — Build/Analyze/Heal AI |
| `FOXYIZ_HEADLESS=true` | Required for verify on Linux servers |

## Post-deploy checklist

1. `curl https://demo.yourdomain.com/api/health` → 200
2. Open `/welcome` → invite redeem flow
3. Open `/signin` → persona grid (no waitlist form)
4. Open `/app` after trial or with admin bypass

   ```bash
   python f/fEngine2.py --config f/fStart_qoa_web_smoke_prod.json
   ```

   Expect smoke green.

5. Optional full verify:

   ```bash
   python f/fEngine2.py --config f/fStart_qoa_web_verify.json
   ```

   Expect **49/49** (`Run=Y`, tag **Verify**).

6. Walk [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md) once with a teammate.

## Bluehost / cPanel

Shared hosting is PHP-first. Use **hybrid**:

- Static marketing on Bluehost → links to VPS demo URL
- Full BRAHL on a $5–10 VPS (Docker above)

## Pre-demo local checklist

1. `python qoa_web/run_local.py`
2. `python u/reset_demo_data.py`
3. `python f/fEngine2.py --config f/fStart_qoa_web_verify.json` → **49/49** green
4. `/welcome` invite → `/signin` → P1 Creator + P3 QA Hunter
5. `/admin` GTM invite batch panel

**BRAHL it** — then demo.
