# Docs — reference hub for humans and AI

**Read this when you open KK/ on a new machine, a new Cursor project, or any other AI tool.**

The goal: **start from docs + a small file slice**, not the whole repo (~90 MB with `z/` history).

---

## Start here (5 minutes)

| Order | File | Why |
|-------|------|-----|
| 1 | [../Summary.md](../Summary.md) | Team index — layout, commands, cloud boundary |
| 2 | [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) | **Agents:** qoa_web scope, verify count, do-not-touch list |
| 3 | [BRAHL.md](./BRAHL.md) | Full BRAHL lifecycle (Build → Run → Analyze → Heal → Loop → Verify) |
| 4 | [FoXYiZ.md](./FoXYiZ.md) | yPAD contract, xReuse, heal rules |
| 5 | [rules.md](./rules.md) | Agent rules — Playwright for explore, yPAD for automate |
| 6 | [HANDOFF.md](./HANDOFF.md) | Minimum export bundle + first commands on a new machine |

**Active app:** qoa_web @ http://127.0.0.1:8765 · **Active suite:** `y/qoa_web/` · **Verify:** **49** plans (`Run=Y`, tag **Verify**) via `f/fStart_qoa_web_verify.json`.

---

## Doc map

| Doc | Audience | Contents |
|-----|----------|----------|
| [README.md](./README.md) | Everyone | This index |
| [HANDOFF.md](./HANDOFF.md) | New machine / export | Slim file list, bootstrap commands |
| [MAINTENANCE.md](./MAINTENANCE.md) | End of session (~30 min) | Cleaner, doc updates, verify hygiene |
| [BRAHL.md](./BRAHL.md) | Deep dive | Phases, loop protocol, qoa_web, version compare |
| [BRAHL_PROMPT.md](./BRAHL_PROMPT.md) | In-app AI | Slim BRAHL context (.md drawer in app) |
| [FoXYiZ.md](./FoXYiZ.md) | yPAD authors | Plans, actions, designs, xReuse, heal table |
| [rules.md](./rules.md) | Agents | Explore vs automate boundaries |
| [test-user-data/README.md](./test-user-data/README.md) | Personas P1–P9 | Source of truth → yPAD D1–D9 |

### Outside Docs/ (linked on purpose)

| Doc | Purpose |
|-----|---------|
| [../Summary.md](../Summary.md) | Root handoff index |
| [../qoa_web/qoa_userDoc.md](../qoa_web/qoa_userDoc.md) | Users & in-app AI — avatars, phases, APIs |
| [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) | Agent memory for qoa_web |
| [../qoa_web/DEPLOY.md](../qoa_web/DEPLOY.md) | Demo / VPS deploy |
| [../pyUtils/README.md](../pyUtils/README.md) | Python utilities (cleaner, yVisualizer, zDefects, zBatchDash) |
| [../f/fStart_SCOPE.md](../f/fStart_SCOPE.md) | Which fStart configs are in scope |

---

## Formula (everywhere)

```
f(x, y) = z
```

| Symbol | Folder | Role |
|--------|--------|------|
| **f** | `f/` | Engine — `fEngine2.py`, `fStart*.json` |
| **x** | `x/` | Actions — `xActions.py`, `xCapa.csv` |
| **y** | `y/<suite>/` | yPAD — plans, actions, designs |
| **z** | `z/<run>/` | Results — CSV, dashboard HTML, BRAHL report (ephemeral) |

**Utilities:** `pyUtils/` — cleaner, persona sync, `zBatchDash.py`. HTML reports: `pyUtils/y_visualization.html`, `pyUtils/zDefectsDashboard.html`. **Not** engine code.

---

## Quick commands (from KK/)

```powershell
python qoa_web/run_local.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json
python pyUtils\sync_personas.py
python pyUtils\cleaner.py --apply
python pyUtils\yVisualizer.py
python pyUtils\zDefects.py
```

See [MAINTENANCE.md](./MAINTENANCE.md) for the full session checklist.

---

## Avatars (qoa_web)

| UI label | Internal key | Role |
|----------|--------------|------|
| **Creator** | client | Post challenges, BRAHL phases, Go/No-Go |
| **QA Hunter** | consultant | Join challenges, deliverables, hunt evidence |
| **Nalanda** | networker | Nalanda community panel — Learn/Teach/Discuss/Invite — no BRAHL phases |

Personas **P1–P9** in [test-user-data/](./test-user-data/) map to yPAD columns **D1–D9**.

---

## What not to index (token efficiency)

`.cursorignore` hides inactive suites (`y/qoa2/`, `y/sunshine/`, …), old `z/` runs, and large binaries. Agents should still read **Docs/** and **Summary.md** — those are the handoff layer.

---

*Last doc pass: 2026-07-05 · Verify target: 49/49 on fStart_qoa_web_verify.json*
