# Next — pick up here (production launch)

Vocabulary: [Docs/terminology.md](Docs/terminology.md) · Runbook: [Docs/PRODUCTION.md](Docs/PRODUCTION.md)

## Just shipped (2026-07-20)

- Pushed `main` → https://github.com/foxyiz/BRAHL (`4c82d18`)
- Cloud Run wiring: `FOXYIZ_CLOUD_WORKER_URL` + `cloud_worker_server.py`
- Env template: `qoa_web/.env.production.example`
- `/api/health` now returns `readiness` (jwt/google/stripe/cloud)
- Backup: `python qoa_web/scripts/backup_data.py`

**Note:** `https://brahl.qaonair.com` was **unreachable** from this network at push time (`Unable to connect`). Ops must bring the web box up / fix DNS, then continue host env steps.

| Priority | Item |
|----------|------|
| P1 | Optional: retag yPAD to only Smoke/UI/API/… (map still works) |
| P1 | `qoa_web_live` journey has **0 API-tagged** plans — add coverage or remap |
| P2 | Deploy / EC2 / Stripe keys on host ([todo.md](todo.md) §4 — billing code ready) |
| P2 | Cloud multi-user sync for schedules/evidence (schema is ready) |
## Host ops (do on the server — secrets stay off git)

1. Sync/deploy `main` to the web box
2. Copy `.env.production.example` → `qoa_web/.env` and fill secrets
3. `python qoa_web/scripts/prod_readiness.py`
4. Google OAuth redirect + Stripe webhook (URLs in PRODUCTION.md)
5. EC2: start `cloud_worker_server.py`; set Arena `FOXYIZ_CLOUD_WORKER_URL`
6. Lock demo: `QOA_ALLOW_DEMO=0`, `QOA_AUTH_REQUIRED=1`, `QOA_ADMIN_OPEN=0`
7. Smoke: `Invoke-RestMethod https://brahl.qaonair.com/api/health`
8. Schedule backups of `qoa_web/data/`

## Local resume

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
python FoXYiZ\pyUtils\cleaner.py --apply
```
