# Deploying BRAHL Web (qoa_web)

**Primary production path:** push/merge to [foxyiz/BRAHL](https://github.com/foxyiz/BRAHL) `main` → auto-deploy to **https://brahl.qaonair.com** every ~6 hours.

Canonical deploy notes (EC2, env, smoke): **[Docs/DEPLOY.md](../Docs/DEPLOY.md)**.

Docker and demo-bundle exports below are **optional** (alternate hosts / offline demos only).

---

## Production (qaonair)

1. Land changes on `main` in the GitHub BRAHL repo (this tree: `qoa_web/` + `FoXYiZ/`).
2. Wait for the ~6h sync (or trigger your team’s job if available).
3. Smoke: `https://brahl.qaonair.com/api/health`
4. Confirm host env: `APP_BASE_URL`, `JWT_SECRET`, `QOA_ADMIN_OPEN`, secrets for OpenAI / EC2.
5. Cloud FoXYiZ runs on **AWS EC2** — Arena `runtime_mode: cloud` wiring is a backlog item; desktop Run works today.

Engine path on disk: `FoXYiZ/f/fEngine2.py` (not root `f/`).

---

## Optional: slim demo export

```powershell
cd KK
python u/export_demo_bundle.py --zip
# → archive/demo-bundle/brahl-demo-<timestamp>/
```

Before verify against a custom host:

```powershell
$env:APP_BASE_URL = "https://your-host.example"
python u/patch_ypad_urls.py
```

### Bundle pieces

| Piece | Purpose |
|-------|---------|
| `qoa_web/api/` | FastAPI |
| `qoa_web/web/` | Static UI |
| `qoa_web/data/` | Writable projects / invites |
| `FoXYiZ/y/…` | yPAD suites as needed |
| `FoXYiZ/f/fEngine2.py` + fStarts | Optional server-side Run |
| `FoXYiZ/x/` | Actions |

**Skip:** fat `FoXYiZ/z/` history, `archive/`, `.git`, unused suites.

### Optional Docker

```bash
cd brahl-demo-<timestamp>
export APP_BASE_URL=https://your-host.example
python u/patch_ypad_urls.py
docker build -t brahl-web -f qoa_web/Dockerfile .
docker run -d -p 8765:8765 \
  -e APP_BASE_URL=$APP_BASE_URL \
  -e QOA_ADMIN_OPEN=1 \
  -e FOXYIZ_HEADLESS=true \
  -v brahl-data:/app/qoa_web/data \
  --name brahl brahl-web
```

### Environment

| Variable | Purpose |
|----------|---------|
| `APP_BASE_URL` | Public site URL |
| `QOA_ADMIN_OPEN` | `1` = Admin open for testing |
| `OPENAI_API_KEY` | Prefer `FoXYiZ/f/.env` |
| `FOXYIZ_HEADLESS=true` | Linux / EC2 headless browser |

### Post-deploy checklist

1. `curl https://brahl.qaonair.com/api/health` → 200  
2. `/welcome` → invite / sign-in  
3. `/app` with project → Build / Run  
4. Confirm Run console streams live while the engine runs  
5. Optional smoke: `python FoXYiZ/f/fEngine2.py --config f/fStart/qoa_web_live.json` from `KK/`

Spelling: **BRAHL** · **FoXYiZ**.
