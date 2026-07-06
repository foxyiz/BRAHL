# Test user data (yPAD suite pointer)

Fictional persona definitions live in **[Docs/test-user-data/](../../Docs/test-user-data/README.md)**.

## Generated files (do not edit by hand)

| File | Generator |
|------|-----------|
| `y3Designs.csv` (persona columns D1–D9) | `gen_persona_ypad.py` |
| `y1Plans.csv`, `y2Actions.csv` | `gen_persona_ypad.py` (persona + verify plans) |
| `qoa_web/web/profiles.js` | `u/sync_profiles_from_docs.py` |

## Regenerate after persona changes

```powershell
cd KK
python u/sync_personas.py
```

- **y3Designs columns D1–D9** map to personas P1–P9 (see `Docs/test-user-data/index.json`).
- API: `GET /api/test-users`, `GET /api/test-users/{id}/fixture`
