# MVP launch checklist

After deploying per [Bluehost.md](./Bluehost.md) and `qoa_web/docker-compose.yml`.

| Check | Pass |
|-------|------|
| `/api/health` returns 200 | |
| `/signup` → `/login` → `/app` with JWT | |
| User menu: Nalanda, A77, Wallet, Theme (not in phase bar) | |
| `+` beside project dropdown creates project | |
| Build: BRAHL Plan generate + accept | |
| Build: Tests / Steps / Test data tabs (not Y Plans jargon) | |
| Cost widget in right rail | |
| No *brawl* / *BRAWL* in UI copy | |
| Run tab mentions FoXYiZ only (no Playwright) | |
| Sign-in draft (`sessionStorage.qoa_draft_requirement`) survives login | |

Local smoke:

```powershell
cd c:\006\FXYZ\KK
pip install -r qoa_web/api/requirements.txt
python qoa_web/run_local.py
python -m pytest qoa_web/api/test_runner_stats.py -q
```
