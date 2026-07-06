# FoXYiZ / BRAHL / qoa_web — Team Summary

**Handoff index for `KK/`** · Last updated: 2026-07-05

**Formula:** `f(x, y) = z` — engine + yPAD → results in `z/`.

**Status:** **qoa_web v1.3** — invite GTM + demo personas. Verify **49/49** green after `reset_demo_data`.

**New machine / new AI:** read [Docs/README.md](Docs/README.md) → [Docs/HANDOFF.md](Docs/HANDOFF.md) → [qoa_web/MEMORY.md](qoa_web/MEMORY.md).

**End of session:** [Docs/MAINTENANCE.md](Docs/MAINTENANCE.md) · `python u/cleaner.py --apply`

---

## Doc map (read this first)

| Doc | Audience |
|-----|----------|
| **Summary.md** (this file) | Team index |
| [Docs/README.md](Docs/README.md) | **Docs hub** — start on new machine |
| [Docs/HANDOFF.md](Docs/HANDOFF.md) | Minimum export bundle |
| [Docs/MAINTENANCE.md](Docs/MAINTENANCE.md) | Session checklist (~30 min) |
| [qoa_web/MEMORY.md](qoa_web/MEMORY.md) | **Cursor agents** — read first for qoa_web |
| [qoa_web/qoa_userDoc.md](qoa_web/qoa_userDoc.md) | **Users & in-app AI** — personas, launch, phases |
| [qoa_web/DEPLOY.md](qoa_web/DEPLOY.md) | VPS / Docker deploy + post-deploy smoke |
| [qoa_web/DEMO_SCRIPT.md](qoa_web/DEMO_SCRIPT.md) | 10-minute team demo walkthrough |
| [Docs/BRAHL.md](Docs/BRAHL.md) | Full BRAHL reference (human / deep dive) |
| [Docs/ATOMIC77.md](Docs/ATOMIC77.md) | **Atomic 77** — idea-to-launch plugin in qoa_web |
| [Docs/FoXYiZ.md](Docs/FoXYiZ.md) | yPAD contract, f(x,y)=z |
| [f/fStart_SCOPE.md](f/fStart_SCOPE.md) | Which fStart configs are in scope |

**Agents:** `qoa_web/MEMORY.md` + `.cursorignore` — skip inactive suites unless asked.

---

## Product snapshot (v1.3)

| Area | Shipped |
|------|---------|
| **GTM funnel** | `/welcome` invite code → 7-day trial → `/signin` persona grid → `/app` arena |
| **Avatars** | Creator · QA Hunter · Nalanda (all profiles can switch) |
| **BRAHL UI** | Build → Run → Analyze → Heal → Loop → BRAHL + **Atomic 77 (A77)** + **$** pricing tab |
| **Persona UX** | Compact dismissible badge (Tips / ×) — not a full task strip |
| **Themes** | **Pro** (text) ↔ **Arena** (visual fight-ring, icon nav, reward rail) |
| **Launch** | Go/No-Go, version compare (baseline vs new), hunt evidence (QA Hunter) |
| **Verify** | **49/49** gate (`Run=Y`, tag **Verify**) — see [CHANGELOG](qoa_web/CHANGELOG.md) |
| **Journey library** | **~800** plans (`y1Plans_journey.csv`, tag **Journey**) — parallel batches via tag fStarts |
| **Batch dashboard** | `python u/zBatchDash.py` → `z/zDash_batch_<name>.html` |

---

## Workspace layout

```
KK/
  f/fEngine2.py         ← engine (do not move to u/)
  x/xActions.py         ← actions (do not move to u/)
  u/                    ← utilities + zBatchDash.py
  y/qoa_web/            ← active suite (49 verify + ~800 journey library)
  z/                    ← run output (ephemeral; run u/cleaner.py)
  qoa_web/              ← web UI + API (port 8765)
  Docs/test-user-data/  ← fictional personas P1–P9 (source of truth)
  archive/cleanup/      ← cleaner output (delete anytime)
  archive/demo-bundle/  ← export_demo_bundle output (optional)
```

---

## Quick run (qoa_web v1.3)

From **`KK/`**:

```powershell
python qoa_web/run_local.py          # → http://127.0.0.1:8765/welcome
python u/reset_demo_data.py          # reset join/submit state before verify
python f\fEngine2.py --config f\fStart_qoa_web_verify.json   # 49 plans (Run=Y)
```

| Config | Suite | Plans | Use |
|--------|-------|-------|-----|
| `fStart_qoa_web_verify.json` | qoa_web | 49 | Full verify (local) |
| `fStart_qoa_web_smoke*.json` | qoa_web | 12 | Quick smoke |
| `fStart_qoa_web_smoke_prod.json` | qoa_web | 12 | Post-deploy (after `patch_ypad_urls`) |
| `fStart_qoa_web_journey_*.json` | qoa_web | 25–181 | Parallel journey batches by tag |

Defaults: **`timeout: 5`** (verify), **`headless: true`** (verify), **`thread_count: 1`**. Use smoke with `headless: false` while debugging UI.

**Parallel batch dashboard** (after multiple journey runs):

```powershell
python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
```

**BRAHL protocol:** Loop 1 full → Loops 2–3 failures-only if needed → restore all `Run=Y` → Verify ×3. Run `reset_demo_data.py` before each full verify.

---

## FoXYiZ essentials

- **yPAD:** `y1Plans`, `y2Actions`, `y3Designs` — edit CSVs directly; no daily Python generators.
- **Expected:** exact string match — empty = presence only.
- **No `xWaitFor`** — use `xGetText`, `xClick`, `xNavigate`.
- **After `xReuse`:** **`xNavigate profile_url`** (or `base_url`) before home-page clicks.

Rebuild **`f/Foxyiz2.exe`** after `xActions.py` changes (see Build exe below).

---

## BRAHL loop (condensed)

```
Build (y/) → Run (f/) → Analyze (z/) → Heal (y/) → Loop → Verify → Report
```

Reports: `z/<timestamp>_<suite>/brahl_report.md` — run **`python u/cleaner.py --apply`** after sessions.

---

## Demo deploy (summary)

1. **Export:** `python u/export_demo_bundle.py --zip`
2. **Prod URLs:** `set APP_BASE_URL=https://demo.yourdomain.com` → `python u/patch_ypad_urls.py`
3. **Run:** `qoa_web/Dockerfile` or `python qoa_web/run_local.py`
4. **Smoke:** `f/fStart_qoa_web_smoke_prod.json` on server
5. **Demo:** [qoa_web/DEMO_SCRIPT.md](qoa_web/DEMO_SCRIPT.md)

Full detail: [qoa_web/DEPLOY.md](qoa_web/DEPLOY.md).

---

## Out of agent scope (unless asked)

| App | Suite | Notes |
|-----|-------|-------|
| qoa2 cloud | `y/qoa2/` | Run/Analyze 404 in cloud |
| Sunshine, ivvu, atomic77 | `y/*` | Archived |

---

## Build exe

`f/Foxyiz2.exe` is **gitignored**. Rebuild after engine changes:

```powershell
cd c:\006\FXYZ\KK
pip install -r f\requirements.txt
pyinstaller --onefile --name Foxyiz2 --paths . ^
  --add-data "x\xActions.py;x" --add-data "z\zDash_template.html;z" ^
  --hidden-import pandas --hidden-import x.xActions ^
  f\fEngine2.py
copy dist\Foxyiz2.exe f\Foxyiz2.exe
```

---

## Cloud vs local (qoa_web deploy boundary)

**Ships to cloud:**

- `qoa_web/` — FastAPI + static web + invite API
- `y/qoa_web/` — suite yPAD
- `Docs/test-user-data/` — persona fixtures
- `f/fStart_qoa_web*.json` — config only
- `u/export_demo_bundle.py`, `u/patch_ypad_urls.py` — deploy helpers

**Stays local or separate worker image:**

- `f/Foxyiz2.exe` / `fEngine2.py` subprocess (Run/Loop)
- Writable `z/`, `qoa_web/data/projects.json`, `qoa_web/data/invites.json`
- Inactive `y/*` suites, `z/` history

**Environment:**

| Variable | Purpose |
|----------|---------|
| `APP_BASE_URL` | Public URL — run `u/patch_ypad_urls.py` before prod verify |
| `QOA_ADMIN_TOKEN` | Protects admin invite export + ecosystem endpoints |
| `OPENAI_API_KEY` | In-app AI (Build, Analyze, Heal, BRAHL chat) |
| `FOXYIZ_HEADLESS` | `true` on Linux servers for FoXYiZ Run tab |

Persona sign-in is **demo-only** (`localStorage` P1–P9). Invite codes unlock 7-day trials; real auth is post-MVP.

---

## Utilities (`u/`)

```powershell
python u/cleaner.py --apply         # archive ephemeral z/ + probes
python u/sync_personas.py           # after editing Docs/test-user-data/
python u/reset_demo_data.py         # reset projects.json before verify
python u/export_demo_bundle.py      # slim VPS deploy bundle
python u/patch_ypad_urls.py         # APP_BASE_URL → yPAD URLs
python u/zBatchDash.py              # aggregate parallel run logs → batch HTML
```

See [u/README.md](u/README.md). **Never** put `fEngine2.py` or `xActions.py` in `u/`.

---

*Apps: qoa_web @ :8765 · qoa2.base44.app · gosunshine.base44.app*
