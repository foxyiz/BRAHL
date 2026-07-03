# qoa_web — Avatars, Build & Human in the Loop

**v1.0** — See also [Summary.md](../Summary.md) and [LAUNCH.md](./LAUNCH.md).

---

## Core rules

1. **All BRAHL phases stay on the active project** — Run / Analyze / Heal / Loop require a selected project.
2. **Client** switches projects or creates new ones; context (chat, + items, budget) is per project.
3. **Human in the Loop** (HITL) consultants join a client project, upload yPADs offline, submit enriched BRAHL reports.
4. **BRAHL automation** (AI + FoXYiZ) handles bulk testing; HITL adds critical issues, UX findings, and offline yPAD work.

---

## Client Build (simplified)

| Element | Purpose |
|---------|---------|
| **AI chat** | Primary input — purpose of the BRAHL cycle |
| **+ button** | Add connector, URL, note, or document path (no fixed JIRA fields) |
| **Budget** | Total $ + slider: automation % vs Human in the Loop % |
| **HITL roster** | Client sees who joined and deliverable counts |

Assistant asks: purpose → connectors (or skip) → set budget.

---

## Human in the Loop Build

1. Browse open client projects  
2. **Join as Human in the Loop**  
3. Read client chat + context (read-only)  
4. Upload yPAD / doc, log deliverables (issues, hours, features)  
5. **Submit Human in the Loop report** → payout preview updates  

Payout split (preview): weighted by critical issues, time, features found, reports submitted.

---

## API (v0.3)

| Endpoint | Purpose |
|----------|---------|
| `POST /api/projects/{id}/chat` | User message + scripted assistant reply |
| `POST /api/projects/{id}/context` | Add + context item |
| `PATCH /api/projects/{id}` | Budget, name, purpose |
| `POST /api/projects/{id}/join-hitl` | Consultant joins project |
| `POST /api/projects/{id}/submit-hitl-report` | HITL report + deliverables |
| `POST /api/projects/{id}/brahl/chat` | BRAHL model Q&A — project + report scoped |
| `GET /api/projects/{id}/brahl/reports` | List reports (automation, HITL, hybrid) |
| `GET /api/projects/{id}/brahl/reports/{run}/content` | Report markdown |
| `POST /api/projects/{id}/brahl/reports` | Link a Verify run to project |

## BRAHL tab (menu)

After Loop, the **BRAHL** button shows all reports for the active project:

| Source type | Meaning |
|-------------|---------|
| Automation | FoXYiZ Verify, no human |
| Automation + AI | BRAHL model assisted runs |
| Human in the Loop | Consultant-enriched report |
| Human + AI / Human + Automation | Hybrid deliverables |

BRAHL model chat only discusses the selected project and the report in view.

---

*Commerce / Stripe — Phase 4 per [PRD.md](./PRD.md).*
