# Docs — slim reference hub

**New chat / new machine:** read in this order:

1. [terminology.md](./terminology.md) — spellings & verbs (**BRAHL**, **FoXYiZ**, **brawled**, yPAD, GO/NO-GO)
2. [HANDOFF.md](./HANDOFF.md) — bootstrap commands + current suites
3. [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) — Arena agent memory
4. [../NEXT.md](../NEXT.md) · [../todaysummary.md](../todaysummary.md) — resume

Goal: **docs + a small file slice**, not the whole `z/` tree.

---

## Keep these (Docs/)

| Doc | Role |
|-----|------|
| [README.md](./README.md) | This index |
| [terminology.md](./terminology.md) | **Shared vocabulary** — start here |
| [HANDOFF.md](./HANDOFF.md) | New-machine / chat handoff |
| [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) | In-app AI — slim lifecycle |
| [AI_GUARDRAILS.md](./AI_GUARDRAILS.md) | In-app AI — token rules |
| [BRAHL_DESKTOP_BYOK.md](./BRAHL_DESKTOP_BYOK.md) | Optional OpenAI key / hosted quotas |
| [BRAHL.md](./BRAHL.md) | Full BRAHL deep dive |
| [FoXYiZ.md](./FoXYiZ.md) | yPAD / heal skill |
| [rules.md](./rules.md) | Agent boundaries |
| [DEPLOY.md](./DEPLOY.md) | VPS / launch checklist |
| [PRODUCTION.md](./PRODUCTION.md) | **Go-live runbook** — env, Google, Stripe, EC2 worker |
| [test-user-data/](./test-user-data/) | Personas P1–P9 → D1–D9 |

Retired (do not re-expand): `archive/docs-retired-20260714/`

---

## Layout

```
KK/
  FoXYiZ/     f · x · y · z · pyUtils
  qoa_web/    Arena + Admin (:8765)
  Docs/       this hub
  archive/    ignored by Cursor
```

**Formula:** `f(x, y) = z` — see [terminology.md](./terminology.md).

---

## Quick commands (from KK/)

```powershell
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream.json        # Smoke
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream_deep.json   # deep lanes
python FoXYiZ\pyUtils\cleaner.py --apply          # archive old z/; keep latest BRAHL run/suite
python FoXYiZ\pyUtils\cleaner.py --apply --ypad-versions   # archive older yPAD version CSVs (keep 2)
python FoXYiZ\pyUtils\sync_personas.py
```

**yPAD history:** major changes → `y/<suite>/versions/<ts>_<label>/` (immutable CSVs). Cleanup archives older snapshots so they leave the AI window; live sheets stay editable.

---

## Active suites (precision)

| Suite | App | fStart | Notes |
|-------|-----|--------|-------|
| `thoughtstream` | https://jusdone.base44.app/ | `thoughtstream.json` + `_deep.json` | Deep v3 · GO · project `0935e530a120` |
| `a77` | Atomic 77 | `a77.json` | Guest-arch smoke/UI |
| `Math` | Math demo | `Math.json` | Lean day smoke |
| `qoa_web_live` | Arena self-test | `qoa_web_live.json` | Gate |
| `nalanda_app` / `ultimate_showdown` | Base44 demos | matching fStart | Optional |

One fStart file per suite under `FoXYiZ/f/fStart/`. Deep ThoughtStream uses a **second** fStart for tag filter only (`thoughtstream_deep.json`).

---

## Avatars

| UI | Key | Role |
|----|-----|------|
| Creator | client | Challenges, BRAHL, Go/No-Go |
| QA Hunter | consultant | Hunt, evidence, payouts |
| Nalanda | networker | Community — no BRAHL phases |

---

## End of session

1. `python FoXYiZ\pyUtils\cleaner.py --apply` (+ `--runtime-scratch` after heal experiments)
2. Update [../todaysummary.md](../todaysummary.md) + [../NEXT.md](../NEXT.md)
3. Keep in-app AI files short (`BRAHL_PROMPT`, `AI_GUARDRAILS`)
4. Do **not** put `Docs/` or `MEMORY.md` in `.cursorignore`

---

*Doc pass: 2026-07-20 · terminology + ThoughtStream deep GO + cleaner keep-latest*
