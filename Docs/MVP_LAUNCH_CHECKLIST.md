# MVP launch checklist

After deploying per [Bluehost.md](./Bluehost.md) and `qoa_web/docker-compose.yml`.

| Check | Pass |
|-------|------|
| `/api/health` returns 200 | |
| `/api/config` shows `allow_demo: false` when `QOA_ALLOW_DEMO=0` | |
| `/signup` → `/login` → `/app` with JWT | |
| `/forgot-password` resets password | |
| Owned projects: User A cannot `GET` User B's owned project (403) | |
| User menu: Nalanda, A77, Wallet, Theme (not in phase bar) | |
| `+` beside project dropdown creates project | |
| Build: BRAHL Plan generate + accept | |
| Build: Tests / Steps / Test data tabs | |
| Cost widget in right rail | |
| No *brawl* / *BRAWL* in UI copy | |
| Run tab mentions FoXYiZ only | |
| Draft requirement survives login (`?restore_draft=1`) | |

Local smoke:

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
python -m pytest qoa_web/api/test_runner_stats.py qoa_web/api/test_auth.py -q
python qoa_web/run_local.py
```
