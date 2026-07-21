# Test plan — ops_overview (deep)

App: https://dashboardpresentation.netlify.app/

| Lane | Focus |
|------|-------|
| Smoke | KPIs, charts, pipeline, Ops Assistant, BRAHL conclusions |
| Func | Q1/Q2 KPI values, period cycle, pipeline stages, targets, shell copy |
| UI | Period filters, 4 KPI drills + close, 6 chart drills, assistant chips/reply, custom range |
| Edge | 404, trailing slash, Q1 chart stability |
| API | GET / + index 200; favicon/robots/manifest/sitemap/unknown 404 (A1) |
| Security | HTTPS + KPI presence |
| Perf | Home < 15s; Q2 filter < 12s |
| Manual | Voice, custom range explore, all KPI drills, mic |

## Verify

| Date | Result | Folder |
|------|--------|--------|
| 2026-07-20 | 23/23 GO (v1) | `z/20260720_132947_ops_overview` |
| 2026-07-21 | 23/23 GO (heal) | `z/20260721_104339_ops_overview` |
| 2026-07-21 | **54/54 GO (deep)** | `z/20260721_105151_ops_overview` |

fStart: `f/fStart/ops_overview.json` (includes Func)  
Deep alias: `f/fStart/ops_overview_deep.json`  
Snapshot before deep: `versions/*_v2-before-deep`
