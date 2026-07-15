# Docs — slim reference hub

**Agents:** start at [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md).  
**Session log:** [../todaysummary.md](../todaysummary.md).  
**Engine operator guide:** [../FoXYiZ/FoXYiZ_Readme.md](../FoXYiZ/FoXYiZ_Readme.md).

Goal: **docs + a small file slice**, not the whole `z/` tree.

---

## Keep these (Docs/)

| Doc | Role |
|-----|------|
| [README.md](./README.md) | This index |
| [HANDOFF.md](./HANDOFF.md) | New-machine / chat handoff |
| [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) | **In-app AI** (packed) — slim lifecycle |
| [AI_GUARDRAILS.md](./AI_GUARDRAILS.md) | **In-app AI** (packed) — token rules |
| [BRAHL_DESKTOP_BYOK.md](./BRAHL_DESKTOP_BYOK.md) | Optional OpenAI key / hosted quotas |
| [BRAHL.md](./BRAHL.md) | Full BRAHL deep dive |
| [FoXYiZ.md](./FoXYiZ.md) | yPAD / heal skill (viewer) |
| [rules.md](./rules.md) | Agent boundaries |
| [DEPLOY.md](./DEPLOY.md) | VPS / launch checklist (+ AWS later) |
| [test-user-data/](./test-user-data/) | Personas P1–P9 (API + sync source) |

Retired (do not re-expand into active Docs): `archive/docs-retired-20260714/`  
(Bluehost long form, AWS design, defects log, prod-site notes, old maintenance).

---

## Layout (current)

```
KK/
  FoXYiZ/     f · x · y · z · pyUtils
  qoa_web/    Arena + Admin SPA
  Docs/       this hub
  archive/    ignored by Cursor
```

**Formula:** `f(x, y) = z` — paths are under `FoXYiZ/` (short `f/…` still works for the engine cwd).

---

## Quick commands (from KK/)

```powershell
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
python FoXYiZ\pyUtils\cleaner.py --apply
python FoXYiZ\pyUtils\sync_personas.py
```

---

## Avatars

| UI | Key | Role |
|----|-----|------|
| Creator | client | Challenges, BRAHL, Go/No-Go |
| QA Hunter | consultant | Hunt, evidence, payouts |
| Nalanda | networker | Community — no BRAHL phases |

Personas **P1–P9** → yPAD columns **D1–D9**. Source: [test-user-data/](./test-user-data/).

---

## Maintenance (end of session)

1. `python FoXYiZ\pyUtils\cleaner.py` then `--apply`
2. Update [../todaysummary.md](../todaysummary.md) if product changed
3. Keep **in-app AI** files short (`BRAHL_PROMPT`, `AI_GUARDRAILS`)
4. Do not put `Docs/` or `MEMORY.md` in `.cursorignore`

---

*Doc pass: 2026-07-14 · lean Docs set + FoXYiZ one-folder layout*
