# qoa_web v1.3 — Agent memory (read this first)

**Status:** v1.3 · lean workspace. Active yPAD: **`y/Math/`** (4-plan Loop/Verify) + **`y/nalanda_app/`**. Fat `y/qoa_web` stays in `archive/`. Phase B Loop proven. **Create challenge** = AI Planner chat (+ voice) → lean yPAD scaffold → optional quick BRAHL + Go/No-Go **scorecard**.

**App:** http://127.0.0.1:8765/welcome · **Arena:** `/app`

**Auth:** `/signup` (social/email → multi-role) · `/login` · JWT · Creator/QA Hunter/Nalanda/**Promoter**. Forms: `web/forms.css`.

**Homepage / menu:** Welcome feature strip — Nalanda · Atomic 77 · **Promoter** · Wallet (same order in arena user menu).

**Handoff:** [Docs/HANDOFF.md](../Docs/HANDOFF.md) · [Docs/MVP_LAUNCH_CHECKLIST.md](../Docs/MVP_LAUNCH_CHECKLIST.md)

---

## In scope (only touch these unless user says otherwise)

| Path | Purpose |
|------|---------|
| `qoa_web/web/` | index.html, app.js, welcome, signin, invite-gate, about |
| `qoa_web/api/` | main.py, runner.py, projects.py, invites.py, pricing.py, ypad.py, ai_* |
| `qoa_web/mcp/server.py` | Cursor MCP bridge |
| `y/Math/`, `y/nalanda_app/` | Lean suites for Loop/Verify/Heal |
| `f/fStart_Math.json`, `f/fStart_nalanda_app_smoke.json` | Primary smoke configs |
| `pyUtils/` | cleaner, persona sync, zBatchDash (not `u/`) |

## Out of scope (do not read/edit in agent sessions)

- `archive/**` (move outside KK when convenient)
- Restored fat `y/qoa_web` / 49-plan verify
- `qoa_web/data/projects.json` unless seed-data work

---

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
# Arena bypass: /app?demo=1

python f\fEngine2.py --config f\fStart_Math.json
# or: f\fStart_nalanda_app_smoke.json

python pyUtils/cleaner.py --apply
```

Restart server after API/UI changes.

---

## Avatars

**Creator** · **QA Hunter** · **Nalanda** — see [qoa_userDoc.md](./qoa_userDoc.md). Unified top bar; Nalanda has no BRAHL phases.

---

## FoXYiZ heal rules

- **Expected** = exact string match; empty = presence only
- No `xWaitFor` — use xGetText/xClick/xNavigate
- After `xReuse`, parent plan must navigate (base_url or profile_url)
- Heal one failing plan at a time; re-run lean smoke

---

## Docs

| Doc | Use |
|-----|-----|
| [Docs/HANDOFF.md](../Docs/HANDOFF.md) | Short session summary |
| [qoa_userDoc.md](./qoa_userDoc.md) | Users, arena, APIs |
| [Docs/BRAHL_DEFECTS.md](../Docs/BRAHL_DEFECTS.md) | Defect closure log |
| [Docs/MVP_LAUNCH_CHECKLIST.md](../Docs/MVP_LAUNCH_CHECKLIST.md) | Launch smoke |
| [Docs/Bluehost.md](../Docs/Bluehost.md) | VPS deploy |
| [Docs/BRAHL.md](../Docs/BRAHL.md) | BRAHL loop |
| [Docs/MAINTENANCE.md](../Docs/MAINTENANCE.md) | End-of-session cleaner |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
