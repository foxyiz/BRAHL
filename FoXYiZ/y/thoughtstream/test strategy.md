# Test strategy — ThoughtStream deep regression v3

App: https://jusdone.base44.app/

## Lanes (FoXYiZ tags)
| Tag | Intent |
|-----|--------|
| Smoke | Launch readiness shell |
| UI | Nav / chrome / AI samples |
| Func | Deep functional regression |
| Edge | Boundary URLs / empty submit / query params |
| Security | Auth gates, XSS query, private view, share/unshare |
| API | Public HTTP GETs (pages + embed.js) |
| Perf | UI load budgets via xStartTimer/xStopTimer |
| Manual | Live mic/LLM/OAuth/OTP/file extract |

## Personas (y3 D1–D3)
| Col | Code | Portfolio |
|-----|------|-----------|
| D1 | P1 Guest Capturer | Solo notes |
| D2 | P2 Guest Researcher | Research threads |
| D3 | P3 Embed Integrator | SDK host apps |

D4–D9 mirror D1 host for now (expand later).

## Run
```powershell
python FoXYiZ/f/fEngine2.py --config f/fStart/thoughtstream.json          # Smoke
python FoXYiZ/f/fEngine2.py --config f/fStart/thoughtstream_deep.json     # Func+Edge+Security+API+Perf
```
