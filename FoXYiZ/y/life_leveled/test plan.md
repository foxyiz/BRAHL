# Test plan — LifeLeveled

| Area | Profile | Plans |
|------|---------|-------|
| Language gate → Home | Smoke | PLife_Smoke_Home |
| Learn / Pricing / About / Privacy | Smoke | PLife_Smoke_* |
| Auth | Smoke + UI | Login, Register, Google |
| Nav / CTAs | UI | NavShell, HomeCTAs |
| 404 | Edge | Unknown404 |
| Host probes | API + Security + Perf | GET + https + load |
| Coach / Onboarding | Manual | HITL |

```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/life_leveled.json
```
