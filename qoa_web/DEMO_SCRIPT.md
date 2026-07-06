# BRAHL Web — 10-minute demo script

Use after deploy or locally at http://127.0.0.1:8765. **GTM funnel:** invite trial → demo personas.

## Pre-flight (5 min)

```powershell
cd KK
python qoa_web/run_local.py
python u/reset_demo_data.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json   # expect 49/49
```

Production: run `python u/patch_ypad_urls.py` then `fStart_qoa_web_smoke_prod.json`.

---

## Demo flow (~10 min)

### 1. Invite landing (1 min)

- Open `/welcome?code=QOA-CR5-001-001-DEMO`
- Redeem code → **7-day trial** starts
- Link to **Try demo profiles** → `/signin`

### 2. Sign-in — pick a profile (1 min)

- Open `/signin` — compact persona grid (no waitlist form)
- Sign in as **P1 · Alex Chen** or **P6 · Morgan Admin**
- Note dismissible **persona badge** on arena (Tips optional)

### 3. Creator — Go/No-Go (3 min)

- Top bar: **Creator** avatar, **My challenge** dropdown
- **Build** → budget, version labels, **Save latest Verify as baseline**
- **BRAHL** tab → **Launch readiness — Go / No-Go** + version compare
- **$** tab → pricing rules + wallet meter

### 4. QA Hunter — hunt evidence (3 min)

- Switch profile to **P3 · Sam Rivera** (or P2 → H avatar)
- **Join as QA Hunter** on Build
- **Hunt evidence** → log a finding, optional screenshot

### 5. Nalanda community (1 min)

- **Nalanda** avatar (N) → single **Nalanda** tab — Learn, Teach, Discuss, Invite
- Post a lesson link, reply in welcome thread, copy personal community invite
- `/about` → Champion vs Contender, invite CTA

### 6. Admin GTM (1 min)

- **P6 · Morgan Admin** → `/admin` → ecosystem stats + **Generate 50 Creator/Hunter invites**

---

## Closing line

> “Enter with an invite, pick a demo profile, and BRAHL your launch readiness. **You Build, We QA — let's BRAHL!**”

---

## Parallel batch ops (optional)

After running journey fStarts in parallel:

```powershell
python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
# → z/zDash_batch_parallel_demo.html
```

See [f/fStart_SCOPE.md](../f/fStart_SCOPE.md).

---

## Invite export (ops)

```bash
curl -H "X-Admin-Token: $QOA_ADMIN_TOKEN" \
  "https://demo.yourdomain.com/api/admin/invites/export?batch_id=BATCH_ID" -o invites.csv
```

Set `QOA_ADMIN_TOKEN` in server env before launch.
