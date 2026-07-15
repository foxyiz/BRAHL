# Today's summary — 2026-07-14

Session log for **KK/** (FoXYiZ + BRAHL Arena / qoa_web). Spelling: **BRAHL** · **FoXYiZ**.

---

## 1. FoXYiZ one-folder layout

Engine pieces no longer sit as sibling `f/ x/ y/ z/ pyUtils/` at repo root. They live under one package:

```
KK/FoXYiZ/{f,x,y,z,pyUtils}
```

- `qoa_web/api/paths.py` maps short paths (`f/…`, `y/…`) → `FOXYIZ_ROOT`.
- Guides: `FoXYiZ/README.md`, `FoXYiZ/FoXYiZ_Readme.md` (skills · memory · yPAD · AI rules).
- Root `README.md` + Cursor rules updated for this layout.
- `.cursorignore` / `.gitignore`: keep `archive/` and `FoXYiZ/z/` out of agent context.

---

## 2. Scoped Admin

- Admin SPA: `qoa_web/web/admin.html|js|css` · APIs `admin_panel.py` / `presence.py`.
- Platform vs project admin · roles in `auth.py` · arena heartbeat · About → `/admin`.
- Demo profile **P6 Super Admin**.

---

## 3. Live Arena smoke (FoXYiZ)

- Suite / configs for `qoa_web_live` gate (+ Admin SPA locators, ClientReady heal).
- Heal helpers under `FoXYiZ/pyUtils/` (e.g. live smoke Admin, y3 Admin smoke).
- Verify gate result cited in session: **20/20** under `FoXYiZ/z/20260714_141404_qoa_web_verify_gate/` (do not paste zResults into chat).

---

## 4. Arena UX — QA agent clarity

- Tagline / copy: **Your QA agent** — FoXYiZ runs tests · BRAHL decides Go/No-Go.
- Phase markers under Build / Run / Analyze / Heal / Loop / BRAHL: aligned under each button, distinct colors (not one green bar).
- Status strip + Loop hint describe the QA-agent Loop (retries · optional Verify · BRAHL report).
- Banner meta in **yPAD** language (plans · steps · data · automated · AI on/off).
- Bottom-right **yPAD dock** above **Wallet**: plans / steps / data / auto + Manual|Automated chips; click → Build coverage.

---

## 5. Build — test strategy.md & test plan.md

- Top of Build **Strategy / plan**: chips for **test strategy.md** and **test plan.md**.
- Click → modal with **Synopsis** / **Full document**.
- API: `GET /api/suites/{suite}/docs` and `…/docs/{strategy|plan}` (`suite_docs.py`).
- Reads `y/<suite>/test_strategy.md` + `test_plan.md` when present; otherwise synthesizes from purpose + yPAD; Accept BRAHL Plan writes both files.

---

## 6. Docs cleanup (this pass)

**Active Docs/ (lean):**

| Keep | Purpose |
|------|---------|
| README, HANDOFF | Hub + bootstrap |
| BRAHL_PROMPT, AI_GUARDRAILS | In-app AI (packed) |
| BRAHL_DESKTOP_BYOK | BYOK / hosted quotas |
| BRAHL.md, FoXYiZ.md | Deep reference |
| rules.md | Agent boundaries (rewritten for FoXYiZ/) |
| DEPLOY.md | VPS + launch checklist (merged) |
| test-user-data/ | Personas P1–P9 (restored from profiles.js) |

**Moved to `archive/docs-retired-20260714/`:**  
`Bluehost.md`, `aws.md`, `MVP_LAUNCH_CHECKLIST.md`, `MAINTENANCE.md`, `BRAHL_DEFECTS.md`, `PROD_AI_UX_NOTES.md`.

Also: removed root `__pycache__` / `.pytest_cache`; `ai_docs.py` drops dead `ATOMIC77.md` / `Summary.md` links; points at this file + `DEPLOY.md` + engine readme.

---

## How to run (after today's changes)

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
# http://127.0.0.1:8765/app?demo=1

python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
python FoXYiZ\pyUtils\cleaner.py --apply
```

Restart the local server after API/UI edits. Optional AI: `OPENAI_API_KEY` in `FoXYiZ/f/.env`.

---

## Still open (not finished today)

- Heal **Apply** beyond AI markdown suggestions.
- Mobile polish for Arena docks / phase nav.
- Production deploy with `QOA_ALLOW_DEMO=0` (see `Docs/DEPLOY.md`).
- Prefer not to expand 800-plan journey CSVs in agent chat; cite suites/zDash only.
