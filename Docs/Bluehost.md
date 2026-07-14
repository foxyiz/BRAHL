# Bluehost — Hosting qoa_web (BRAHL Web)

Short guide for putting **qoa_web** on Bluehost. The app is a **Python FastAPI** server (`uvicorn` on port **8765**), not a static PHP site.

**Related:** [qoa_web/DEPLOY.md](../qoa_web/DEPLOY.md) · [qoa_web/Dockerfile](../qoa_web/Dockerfile) · [qoa_web/deploy/nginx.conf.sample](../qoa_web/deploy/nginx.conf.sample)

---

## 1. Pick the right Bluehost product

| Bluehost plan | Good for qoa_web? | Why |
|---------------|-------------------|-----|
| **Shared hosting** (basic cPanel) | **No** (full app) | PHP-first; no reliable always-on Python API + writable `data/` + optional FoXYiZ |
| **VPS / Cloud** | **Yes** | You control Python, Docker, nginx, HTTPS, PostgreSQL |
| **Hybrid** | **Yes** (common) | Marketing site on shared Bluehost → app on VPS |

**Recommendation:** Use **Bluehost VPS or Cloud** for the app. Use shared hosting only for a landing page that links to the app.

---

## 2. What you are deploying

### Minimum (web UI + API — demo / arena)

| Folder / file | Purpose |
|---------------|---------|
| `qoa_web/api/` | FastAPI backend |
| `qoa_web/web/` | Frontend (`/welcome`, `/signin`, `/app`) |
| `qoa_web/data/` | `projects.json`, invites — **must be writable** |
| `f/.env` | Secrets (see §6) |

### Optional (Run / Verify on the server)

| Piece | Purpose |
|-------|---------|
| `f/fEngine2.py`, `f/fStart_*.json` | FoXYiZ test runs |
| `x/`, `y/<suite>/` | Actions + yPAD |
| `FOXYIZ_HEADLESS=true` | Required on Linux servers |

**Do not upload** the whole `KK/` tree (~90 MB with `z/` history). Use the slim bundle:

```powershell
cd c:\006\FXYZ\KK
python u/export_demo_bundle.py --zip
# → archive/demo-bundle/brahl-demo-<timestamp>/
```

> **Note:** `y/qoa_web/` may be removed locally to save context. Restore it before server-side verify, or deploy **UI-only** against existing `z/` results.

---

## 3. Domain & DNS

1. In Bluehost: **Domains** → point `demo.yourdomain.com` to your VPS IP (**A record**).
2. On the VPS: nginx + **Let's Encrypt** for HTTPS (§5).
3. Patch test links to your public URL **before** verify:

```powershell
$env:APP_BASE_URL = "https://demo.yourdomain.com"
python u/patch_ypad_urls.py
```

---

## 4. Deploy on Bluehost VPS (Docker Compose — preferred)

From the demo-bundle or `KK/` root:

```bash
export APP_BASE_URL=https://demo.yourdomain.com
export JWT_SECRET=$(openssl rand -hex 32)
export QOA_ADMIN_TOKEN=$(openssl rand -hex 16)
export QOA_ALLOW_DEMO=0
export POSTGRES_PASSWORD=$(openssl rand -hex 16)

cd qoa_web
docker compose up -d --build
```

This starts **Postgres** + **brahl-web** ([docker-compose.yml](../qoa_web/docker-compose.yml)). Auth users live in SQLite under `qoa_web/data/users.db` on the data volume; `DATABASE_URL` is reserved for a future projects-DB migration.

Check:

```bash
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/config   # allow_demo should be false when QOA_ALLOW_DEMO=0
```

Users open: `https://demo.yourdomain.com/welcome` → `/signup` or `/login`

### Single-container alternative

```bash
docker build -t brahl-web -f qoa_web/Dockerfile .
docker run -d -p 8765:8765 \
  --name brahl \
  --restart unless-stopped \
  -e APP_BASE_URL=$APP_BASE_URL \
  -e JWT_SECRET=$JWT_SECRET \
  -e QOA_ADMIN_TOKEN=your-long-secret \
  -e QOA_ALLOW_DEMO=0 \
  -e FOXYIZ_HEADLESS=true \
  -v brahl-data:/app/qoa_web/data \
  brahl-web
```

---

## 5. HTTPS with nginx

Copy `qoa_web/deploy/nginx.conf.sample` → `/etc/nginx/sites-available/brahl-demo`, replace `demo.yourdomain.com`, enable the site, then:

```bash
sudo certbot --nginx -d demo.yourdomain.com
sudo systemctl reload nginx
```

---

## 6. Environment variables

| Variable | Required? | Purpose |
|----------|-----------|---------|
| `APP_BASE_URL` | **Yes** (public URL) | Links in yPAD / personas |
| `QOA_ADMIN_TOKEN` | **Yes** (production) | Protects `/admin` APIs |
| `OPENAI_API_KEY` | Optional | AI on Build / Analyze / Heal |
| `FOXYIZ_HEADLESS=true` | If running tests on server | Headless FoXYiZ |
| `QOA_ALLOW_DEMO` | **Yes** (set `0` in prod) | Disables `?demo=1` invite bypass |
| `JWT_SECRET` | **Yes** (production) | Signs login tokens |
| `DATABASE_URL` | Optional (compose sets it) | Reserved; users DB is SQLite in `data/users.db` today |
| `SMTP_*` | **Yes** (production auth) | Verification + password reset email |

Put secrets in `f/.env` on the server (not in the browser). The Build tab **ENV** panel is reference only.

---

## 7. Production sign up / sign in (required for public cloud)

**Today (demo):** `/signin` picks **P1–P9 test personas** with **no password**; identity lives in browser `localStorage`. That is **not** production auth.

**Before public launch on Bluehost Cloud**, you need **real server-side accounts**:

| Feature | Required |
|---------|----------|
| Sign up (email + password or OAuth) | Yes |
| Sign in / sign out | Yes |
| Forgot password + email reset | Yes |
| Email verification | Recommended |
| API protection | Every `/api/projects/*` call must know the logged-in user |
| Per-user data | Projects, wallet, invites scoped to `user_id` — not shared `projects.json` |

### Architecture (simple)

```
Browser → HTTPS (nginx) → FastAPI (uvicorn :8765)
                              → Auth (sessions or JWT)
                              → PostgreSQL (users, projects)
```

**Do not** rely on `localStorage` for identity in production.

### Two paths

| Path | Best for |
|------|----------|
| **A — Managed auth** (Clerk, Auth0, Supabase Auth, Firebase) | Fastest launch; vendor handles passwords, OAuth, reset |
| **B — Custom FastAPI + PostgreSQL** | Full control; you own security (bcrypt, rate limits, CSRF) |

### What to change in the app

1. Replace persona-only `/signin` with email/password (or “Continue with Google”).
2. Replace `localStorage` profile checks in `app.js` with server session / JWT.
3. Migrate `projects.json` → DB rows with `owner_user_id`.
4. Scope APIs — users see only their projects.
5. Optional: keep **invite codes** as a gate before signup (existing `invites.json` flow).
6. **Disable** `?demo=1` bypass on production.
7. Configure **SMTP** (Bluehost mail or SendGrid) for verification and reset emails.

### Rollout order

1. Deploy stack on VPS (§4–5).
2. Add PostgreSQL + auth (Path A or B).
3. Wire signup/signin pages and protect APIs.
4. Migrate projects off shared JSON.
5. Optional: invite code → then create account (GTM funnel).

---

## 8. Hybrid: shared Bluehost + VPS app

1. **Shared Bluehost:** static homepage at `yourdomain.com` with a button → `https://demo.yourdomain.com/welcome`.
2. **VPS:** runs the Docker stack (§4).
3. No Python required on shared hosting.

---

## 9. After deploy — quick test

1. `curl https://demo.yourdomain.com/api/health` → `200`
2. Open `/welcome` → invite flow (or signup when auth is live)
3. Open `/signin` → login (not demo personas in production)
4. Open `/app` — Build tab loads
5. Run tab works only if FoXYiZ + yPAD are on the server

Optional smoke (when yPAD is present):

```bash
python f/fEngine2.py --config f/fStart_qoa_web_smoke_prod.json
```

Walk [qoa_web/DEMO_SCRIPT.md](../qoa_web/DEMO_SCRIPT.md) once with a teammate.

---

## 10. Common problems

| Problem | Fix |
|---------|-----|
| **502 Bad Gateway** | Container not running: `docker ps`, `docker logs brahl` |
| **Port in use** | Change mapping: `-p 8080:8765` and update nginx upstream |
| **Writes fail** | Ensure `qoa_web/data/` is writable (`-v brahl-data:...`) |
| **AI off everywhere** | Set `OPENAI_API_KEY` in `f/.env`, restart container |
| **Verify fails on server** | Need `y/<suite>/`, `x/`, Chrome headless; `FOXYIZ_HEADLESS=true` |
| **Shared hosting only** | Host marketing HTML only; move app to VPS |
| **Users see each other's projects** | Production auth + per-user DB not deployed yet (§7) |

---

## 11. Mental model

```
Browser  →  https://demo.yourdomain.com  →  nginx (443)
                                              ↓
                                         uvicorn :8765  (qoa_web/api/main.py)
                                              ↓
                                         qoa_web/data/  (JSON — demo only)
                                         PostgreSQL     (production users + projects)
                                         optional: f/fEngine2.py → z/
```

Locally you run `python qoa_web/run_local.py` (`127.0.0.1:8765`). In cloud, the same app binds `0.0.0.0:8765` behind nginx.

---

## 12. Bottom line

| Goal | Where |
|------|--------|
| Domain + marketing page | Bluehost **shared** |
| Full qoa_web app | Bluehost **VPS / Cloud** (or any VPS + Bluehost DNS) |
| Real users | **§7 auth** — not included in demo persona flow |
