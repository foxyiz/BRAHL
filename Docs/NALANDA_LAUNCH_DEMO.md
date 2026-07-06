# Nalanda SkillFlow AI — full platform launch demo

End-to-end story: a **Creator** brings [Nalanda SkillFlow AI](https://nalanda.base44.app/) into QA on Air, runs FoXYiZ smoke, invites a **QA Hunter**, shares learn paths on **Nalanda**, and lands a **Go/No-Go** on BRAHL.

---

## What we scaffolded

| Asset | Purpose |
|-------|---------|
| `y/nalanda_app/` | FoXYiZ yPAD for [Nalanda SkillFlow AI](https://nalanda.base44.app/) — **y3Designs D1–D9** persona template + app URLs |
| `f/fStart_nalanda_app_smoke.json` | Run config (`headless: false`) |
| `qoa_web/data/nalanda_launch.seed.json` | Demo project with Creator prompt + QA Hunter stories |
| `u/reset_demo_data.py` | Loads **qoa_web Local** + **Nalanda Launch** into `projects.json` |

---

## 1. Bootstrap

```powershell
cd c:\006\FXYZ\KK
python u/reset_demo_data.py
python qoa_web/run_local.py
```

- Arena: http://127.0.0.1:8765/app?demo=1  
- Sign in as **P1 · Alex Chen** (Creator)

---

## 2. Creator — Build (capture the prompt)

1. Top bar → select **Nalanda SkillFlow AI — Launch Readiness**
2. **Build** tab — you should see the seeded chat:
   > *Here is my web app https://nalanda.base44.app/ — we're ready for launch. Give me a health report and Go/No-Go.*
3. Confirm **context chip**: Production app → nalanda.base44.app
4. Set budget (e.g. $500, 55/45 automation vs QA Hunter)
5. **Invite QA Hunter** with tag `launch-mobile-ux`

This is the “prompt → project” moment the platform records in `projects.json`.

---

## 3. Run — FoXYiZ smoke (fill the yPAD)

In **Run** tab:

- Suite: **nalanda_app**
- Config: `f/fStart_nalanda_app_smoke.json`
- Click **Run**

Or from shell (browser visible):

```powershell
python f\fEngine2.py --config f\fStart_nalanda_app_smoke.json
```

**Plans (tag `NalandaApp`):**

| Plan | Checks |
|------|--------|
| `PNalanda_Smoke_Landing` | Title + hero h1 |
| `PNalanda_Smoke_Explore` | `/explore` |
| `PNalanda_Smoke_LearningPath` | `/LearningPath` |
| `PNalanda_Smoke_Quiz` | `/Quiz` |
| `PNalanda_Smoke_AITutor` | `/ai-tutor` |
| `PNalanda_Launch_Health` | All core routes in one pass |

Results land in `z/<timestamp>_nalanda_app/`.

### y3Designs — persona test data

The **Y Designs** tab shows **D1–D9** columns labeled by persona name (Alex Chen, Jordan Lee, …). Shared Nalanda URLs and locators are identical across columns; fill per-persona credentials in `login_email` / `login_password` when you add auth flows.

---

## 4. QA Hunter — human pass

1. Switch avatar **H** (or sign in **P3 · Sam Rivera**)
2. Select the same challenge in the top bar → **Join as QA Hunter**
3. Work the seeded stories:
   - Mobile learning path UX
   - Quiz happy path
   - AI Tutor first message
4. **Hunt evidence** (optional recording) → **Submit QA Hunter report** — recordings persist until submit; hunt report + `.webm` replay on **BRAHL** tab

---

## 5. Nalanda — community corner

1. Switch avatar **N** (Nalanda)
2. **Teach** — post a lesson linking nalanda.base44.app + ITelearn
3. **Discuss** — reply in welcome thread
4. **Invite** — copy personal community link for peers

This captures how Nalanda contributed alongside Creator + QA Hunter.

---

## 6. BRAHL — health report & Go/No-Go

1. Back to **Creator** avatar
2. **Analyze** → refresh runs → review failures (T1/T2/T3)
3. **Loop** → generate BRAHL report from latest verify run
4. **BRAHL** tab → read markdown report; QA Hunter hunt reports appear with **QA Hunter** badge and video playback; ask:
   > *Executive summary — are we Go or No-Go for launch?*
5. **Go/No-Go** block on BRAHL tab — set verdict with rationale
6. Optional: **Save baseline** on Build → run again after a deploy → **Version compare**

---

## 7. Extend the yPAD (your next Build iteration)

Edit `y/nalanda_app/y1Plans.csv` / `y2Actions.csv` / `y3Designs.csv`:

- Add login flow if auth is required
- Add `xAPI` health checks if Base44 exposes `/api/health`
- Tag new plans `NalandaApp;Launch` and re-run

FoXYiZ skill: [Docs/FoXYiZ.md](../Docs/FoXYiZ.md)

---

## Closing narrative (demo script)

> Creator entered the launch prompt on Build. FoXYiZ proved core routes load. QA Hunter enriched the report with UX evidence. Nalanda shared the learn path and invite link. BRAHL synthesized a Go/No-Go — **You Build, We QA — let's BRAHL!**
