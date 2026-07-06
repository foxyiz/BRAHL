# Test user data (fictional)

Fictional BRAHL Web personas for local QA — **not real users**. Source of truth for sign-in profiles, persona journeys, and FoXYiZ yPAD design columns **D1–D9**.

## Layout

| File | Purpose |
|------|---------|
| [index.json](./index.json) | Persona registry + yPAD column mapping |
| [p1-alex-chen.json](./p1-alex-chen.json) … [p9-casey-nguyen.json](./p9-casey-nguyen.json) | Per-persona tasks, sample data, verify tags |

## FoXYiZ mapping (y/qoa_web)

| y3Designs column | Persona | Default avatar |
|------------------|---------|----------------|
| D1 | P1 Alex Chen | Creator |
| D2 | P2 Jordan Lee | Creator (dual) |
| D3 | P3 Sam Rivera | QA Hunter |
| D4 | P4 Dr. Priya Nair | QA Hunter (senior) |
| D5 | P5 Chris Martinez | Creator (manual) |
| D6 | P6 Morgan Admin | Creator (admin) |
| D7 | P7 Taylor Kim | Creator (power) |
| D8 | P8 Riley Okonkwo | QA Hunter (bounty) |
| D9 | P9 Casey Nguyen | New user (NUX, empty state) |

Regenerate yPAD from this folder:

```powershell
cd KK
python u/sync_personas.py
```

## API (qoa_web)

- `GET /api/test-users` — list personas
- `GET /api/test-users/{id}` — full persona + tasks + sample_data
- `GET /api/test-users/{id}/tasks?avatar=client|consultant` — tasks for current avatar
- `GET /api/test-users/{id}/fixture` — preload bundle for UI / demos

Deep-link: `http://127.0.0.1:8765/?profile=p2&suite=qoa_web`
