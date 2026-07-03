# qoa_web Changelog

## 1.0.0 — 2026-07-03

**Local BRAHL web — production-ready desktop release**

### Features
- Full six-phase BRAHL UI: Build, Run, Analyze, Heal, Loop, BRAHL
- Client vs HITL avatars with project-scoped context
- Add project modal, build checklist, locked-phase CTAs, role-switch modal
- Context strip (status + project meta), consultant filter/sort/compact mode
- Phase progress indicator across the BRAHL cycle
- Run: suite picker + fStart config + live job log
- Analyze: run list, failures table, zDash link
- Heal: shrink to failures / restore Run=Y (BRAHL.py parity)
- Loop: Step 0, Loop 1/2/3, Verify with auto shrink/restore, cycle history, report generate
- BRAHL tab: report list, viewer, model chat, link verify run
- REST API including `/api/version`, `/api/ypad/shrink`, `/api/ypad/restore`, cycle history
- FoXYiZ verify suite: 50 plans (UI + API)

### v1.0.1 — dual avatar verify

- HITL reuse plan `PReuse_qoa_web_HitlReady`
- 10 HITL-specific UI/API plans (Run, Analyze, Heal, Loop, BRAHL scoped)
- Consultant auto-select first project on gate entry
- **60/60** FoXYiZ verify · [LAUNCH.md](./LAUNCH.md)

- [x] Web UI runs qoa_web verify and shows zDash
- [x] Step 0 saves context JSON with project link
- [x] Loop 1 → Verify → Report flow in browser
- [x] BRAHL.py shrink/restore parity in Heal + Loop
- [x] MCP helper script for Cursor agents

## 0.5 — 2026-07-03
- Context strip, consultant toolbar, mobile topbar polish

## 0.4 — 2026-07-03
- Add project modal, checklist, locked CTAs, role-switch modal

## 0.3 — 2026-07-03
- Six phases, avatars, project scope, BRAHL reports tab
