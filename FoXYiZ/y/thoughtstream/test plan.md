# Test plan — ThoughtStream deep v3

Expanded yPAD beyond shallow smoke: functional, edge, security, API, performance.

| Lane | Auto focus |
|------|------------|
| Func | Mode switch, type thought, samples→ideas/dashboard/detail, docs/integrate depth, personas D2/D3 |
| Edge | /idea/, missing id, /view/, traversal, long 404, empty login, bad email, query params |
| Security | Private view, embed gate, XSS query, unshare, https host, docs auth |
| API | GET /, /embed.js, /docs, /integrate, /login, /ideas, /dashboard, /embed, favicon, unknown |
| Perf | Home/Docs/Ideas/Integrate/Login load < 15s |
| Manual | Fresh InvokeLLM, silent audio, OTP, cross-browser public, large-N perf |

fStarts: `thoughtstream.json` (Smoke) · `thoughtstream_deep.json` (deep tags)

## Verify (2026-07-20)

| Lane | Result | Folder |
|------|--------|--------|
| Deep (Func+Edge+Security+API+Perf) | **49/49** | `z/20260720_124346_thoughtstream` |
| Snapshot | v3-deep-regression | `y/thoughtstream/versions/20260720_124808_v3-deep-regression` |
| BRAHL | GO | Arena project `0935e530a120` |

yPAD: **92** plans · **77** Run=Y · **15** Manual(Run=N)
Personas: D1 Guest Capturer · D2 Guest Researcher · D3 Embed Integrator
