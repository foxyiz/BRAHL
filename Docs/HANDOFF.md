# Handoff — short session summary (2026-07-14)

Use this instead of the long chat transcript. Read `qoa_web/MEMORY.md` first.

## Product

- **KK/** = FoXYiZ engine + **qoa_web** (BRAHL arena) at http://127.0.0.1:8765
- Naming: always **BRAHL**; spelling **FoXYiZ**

## Done recently

- Defect closure notes: `Docs/BRAHL_DEFECTS.md`
- Plan-level stats API + zDash path fix + Loop recovery UI bits
- Auth (signup/login/JWT), project ownership, MVP checklist, Bluehost notes
- Build BRAHL Plan generate/accept path

## Lean KK cleanup (this session)

Moved noise into **`archive/`** so you can relocate the whole folder out of KK:

| Bucket | What |
|--------|------|
| `archive/cleanup/<ts>/` | Ephemeral `z/` runs + brahl reports (`cleaner.py --apply`) |
| `archive/not-needed-20260714/` | Unused `y/*` (qoa2, ivvu, …), unused `fStart_*`, Issues.docx/pdf/extracts, Summary.md, BRAHL.py, test-user-data |

**Still in KK:** `qoa_web/`, `f/` (engine + Math/nalanda/qoa_web smoke-verify starts), `x/`, `y/Math`, `y/nalanda_app`, `pyUtils/`, slim `Docs/*.md`.

`f/Foxyiz2.exe` (~69MB) stays for local runs; already gitignored.

## Active next plan (lean roadmap)

1. **A** — hygiene done ✔
2. **B** — Loop 1/2/3 + Verify on **Math** ✔ (4-plan smoke; shrink/restore baseline; P-prefix PlanId fix)
3. **C** — Heal **Apply** beyond AI markdown
4. **D** — Classical BRAHL report Go/No-Go UI
5. **E** — zDash check, uninvite, nav flake, Tests CSS, mobile
6. **F** — GitHub + Bluehost (`QOA_ALLOW_DEMO=0`)
7. **G later** — Career Assistant, voice CS, screenshots, deep Nalanda, waitlist

### Phase B proof (Math)

- Suite: `y/Math/` — 4 Run=Y plans (Addition, Multiplication, Modulo, Round)
- fStart: `f/fStart_Math_smoke.json` / `f/fStart_Math_verify.json`
- Shrink saves `y/Math/Math_run_y_baseline.json`; restore reapplies that set
- Unit: `qoa_web/api/test_ypad_loop.py`

## AI bootstrap (@-mention only these)

1. `qoa_web/MEMORY.md`
2. `Docs/HANDOFF.md` (this file)
3. `Docs/BRAHL.md` / `Docs/MVP_LAUNCH_CHECKLIST.md` as needed

After work: `python pyUtils/cleaner.py --apply`. Safe to delete or move `archive/` anytime.
