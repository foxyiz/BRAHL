# Test plan — Konfiga (FoXYiZ.exe package)

App: https://konfiga.com/

| Lane | Focus |
|------|-------|
| Smoke | Home hero, features, workflow, framework cards, CTAs |
| UI | #features / #how-it-works / #agent-form anchors |
| Edge | Unknown 404 + A1 broken nav routes (create/framework/login/upload) |
| API | GET / 200; favicon/robots/manifest/unknown 404 |
| Security / Perf | HTTPS; home < 15s |
| Manual | Agent creator form, Try/Deploy |

```powershell
cd FoXYiZ\packaging\dist\FoXYiZ_user
.\f\FoXYiZ.exe --config f\fStart\konfiga.json
```
