# Test plan — ops_overview v1

App: https://dashboardpresentation.netlify.app/

| Lane | Focus |
|------|-------|
| Smoke | KPIs, charts, pipeline, Ops Assistant, BRAHL conclusion |
| UI | Period Q2/H1, drill-down, assistant panel, custom range |
| Edge | Unknown path 404 |
| API | GET / + index 200; favicon/robots/unknown 404 (A1 assets) |
| Security | HTTPS public dashboard |
| Perf | Home < 15s |
| Manual | Voice assistant, custom range explore |

fStart: `f/fStart/ops_overview.json`
