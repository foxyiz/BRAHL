# qoa_web workspace data

## projects.json

Runtime workspace metadata: chat history, budget, HITL roster, BRAHL report links per project.

- **Loaded by:** `qoa_web/api/projects.py` at server start
- **Local dev:** full seed (~32 KB, 7 demo projects) — excluded from Cursor index (`.cursorignore`)
- **Cloud deploy:** start from [`projects.seed.json`](./projects.seed.json) and grow via API

Reset local demo data:

```powershell
python u/reset_demo_data.py
```

## invites.json

GTM invite codes and redemption state. Seeded from [`invites.seed.json`](./invites.seed.json) on first run.

- **Loaded by:** `qoa_web/api/invites.py`
- **Admin:** batch generate + CSV export on `/admin` (requires `QOA_ADMIN_TOKEN`)

Demo codes: `QOA-CR5-001-001-DEMO`, `QOA-QH5-001-001-DEMO`.

## nalanda.json

Nalanda community data: lessons, discussion threads, personal invite codes per profile.

- **Loaded by:** `qoa_web/api/nalanda.py` at server start
- **Seed:** [`nalanda.seed.json`](./nalanda.seed.json) — welcome thread + featured Nalanda/ITelearn lessons
- **Reset:** included in `python u/reset_demo_data.py`

Personal invite codes sync to `invites.json` via `register_nalanda_personal_code()`.

## nalanda_app suite (external launch smoke)

FoXYiZ yPAD for [Nalanda SkillFlow AI](https://nalanda.base44.app/) — used by the **Nalanda SkillFlow AI — Launch Readiness** demo project.

- **Suite:** `y/nalanda_app/` · **Run:** `python f/fEngine2.py --config f/fStart_nalanda_app_smoke.json`
- **Walkthrough:** [Docs/NALANDA_LAUNCH_DEMO.md](../../Docs/NALANDA_LAUNCH_DEMO.md)

## waitlist.json (legacy)

Optional email capture from early hybrid MVP. Sign-in UI removed in v1.3; file may still exist for legacy API. Safe to ignore for new deploys focused on invite GTM.

## Scaffolding new app suites

When a Creator clicks **Add challenge**, `qoa_web/api/runner.py` calls `u/scaffold_app_ypad.py` to create:

| Output | Contents |
|--------|----------|
| `y/<suite>/y3Designs.csv` | D1–D9 persona meta (`persona_name`, credentials placeholders) + `base_url` |
| `y/<suite>/y1Plans.csv` | Open-site reuse + landing smoke |
| `y/<suite>/y2Actions.csv` | Starter actions referencing `DataName` tokens |
| `f/fStart_<suite>_smoke.json` | FoXYiZ smoke run config |

Regenerate manually: `python u/scaffold_app_ypad.py my_app https://example.com/`

## Generated artifacts (personas)

| Output | Source | Regenerate |
|--------|--------|------------|
| `qoa_web/web/profiles.js` | `Docs/test-user-data/` | `python u/sync_personas.py` |
| `y/qoa_web/y1Plans.csv`, `y2Actions.csv`, `y3Designs.csv` | same | `python u/sync_personas.py` |

Do not hand-edit `profiles.js`. Edit persona JSON under `Docs/test-user-data/` then run sync.

See [Docs/test-user-data/README.md](../../Docs/test-user-data/README.md).
