# qoa_web v1.3 — Agent memory (read this first)

**Status:** v1.3 invite GTM · **yPAD `y/qoa_web/` removed** (too large / context noise) — to be re-added later. Reporting/UI reads from `z/` runs; Run/Loop/Verify + shrink/restore need the yPAD restored first.

**App:** http://127.0.0.1:8765/welcome · **Arena:** `/app` · **Test project:** qoa_web Local (`d21afcefc002`)

**Avatars (user-facing):** **Creator** (`client`) · **QA Hunter** (`consultant`) · **Nalanda** (`networker`) — all profiles can switch; see [qoa_userDoc.md](./qoa_userDoc.md).

**Handoff:** [Docs/README.md](../Docs/README.md) · [Docs/HANDOFF.md](../Docs/HANDOFF.md) · [Summary.md](../Summary.md)

---

## In scope (only touch these unless user says otherwise)

| Path | Purpose |
|------|---------|
| `qoa_web/web/` | index.html, app.js, welcome, signin, invite-gate, about |
| `qoa_web/api/` | main.py, runner.py, projects.py, invites.py, pricing.py, ypad.py, ai_* |
| `qoa_web/mcp/server.py` | Cursor MCP bridge |
| `y/qoa_web/` | **Removed** — yPAD (y1Plans/y2Actions/y3Designs) to be re-added later |
| `Docs/test-user-data/` | Persona source of truth (P1–P9) |
| `f/fStart_qoa_web_*.json` | verify / journey / smoke configs — inert until `y/qoa_web/` is restored |
| `u/` | cleaner, persona sync, zBatchDash |

## Out of scope (do not read/edit in agent sessions)

- `y/qoa2/`, `y/sunshine/`, `y/ivvu/`, `y/atomic77/`
- Other `f/fStart*.json` (see `.cursorignore`)
- `qoa_web/data/projects.json` unless seed-data work

---

## Commands

```powershell
cd c:\006\FXYZ\KK

python qoa_web/run_local.py
# Landing: http://127.0.0.1:8765/welcome  ·  Arena: http://127.0.0.1:8765/app
# GTM invite demo codes: QOA-CR5-001-001-DEMO (Creator) · QOA-QH5-001-001-DEMO (Hunter)
# Dev bypass: /app?demo=1 or footer bypass on welcome

python u/reset_demo_data.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json

# Parallel journey (6 terminals — tags on y1Plans_journey.csv):
# fStart_qoa_web_journey_api.json, _brahl, _external, _cost, _foxyiz, _qahunter
# After all finish: python u/zBatchDash.py --name parallel_demo --logs z/parallel_demo_*.log
# → z/zDash_batch_parallel_demo.html

python u/sync_personas.py
python u/cleaner.py --apply
```

Restart server after API/UI changes. Tests use `/app?reset=1&demo=1` (`fresh_url` in y3Designs).

---

## Avatars (verify must stay green)

| Avatar | Reuse plan | Key tests |
|--------|------------|-----------|
| **Creator** | `PReuse_qoa_web_ClientReady` | Build, BRAHL, Go/No-Go, version compare |
| **QA Hunter** | `PReuse_qoa_web_HitlReady` | Join, deliverables, hunt evidence |
| **Nalanda** | (same shell as Creator) | Nalanda panel — Learn/Teach/Discuss/Invite — no BRAHL phases |

Unified UX — same top bar; labels vary (**My challenge** vs **Open challenges**).

---

## FoXYiZ heal rules

- **Expected** = exact string match; empty = presence only
- No `xWaitFor` — use xGetText/xClick/xNavigate
- After `xReuse`, parent plan must navigate (base_url or profile_url)
- Heal one failing plan at a time; re-run verify

---

## Docs

| Doc | Use |
|-----|-----|
| [qoa_userDoc.md](./qoa_userDoc.md) | Users, arena, APIs, personas |
| [Docs/BRAHL_DEFECTS.md](../Docs/BRAHL_DEFECTS.md) | Defect closure log |
| [Docs/MVP_LAUNCH_CHECKLIST.md](../Docs/MVP_LAUNCH_CHECKLIST.md) | Post-MVP launch smoke |
| [Docs/Bluehost.md](../Docs/Bluehost.md) | VPS deploy + auth |
| [Docs/BRAHL.md](../Docs/BRAHL.md) | Full BRAHL loop + qoa_web quick ref at top |
| [Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) | End-of-session cleaner + doc sync |
| [u/README.md](../u/README.md) | cleaner, persona sync, zBatchDash |
| [Summary.md](../Summary.md) | Team index + cloud boundary |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |

**Deprecated:** launch and avatar build notes — merged into [qoa_userDoc.md](./qoa_userDoc.md).
