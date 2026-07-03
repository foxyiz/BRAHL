# Research — Why qoa2.base44.app Cannot Run FoXYiZ Today

**Date:** 2026-07-03  
**Purpose:** Inform `qoa_web` architecture — what blocks cloud execution and how to fix it.

---

## 1. Current topology

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  qoa2.base44.app (Base44)   │     │  Developer desktop (KK/)     │
│  ─────────────────────────  │     │  ──────────────────────────  │
│  • React UI / BRAHL pages   │     │  • fEngine2.py / Foxyiz2.exe │
│  • Base44 backend / DB      │  ✗  │  • xActions + Selenium       │
│  • No Selenium              │ no  │  • y/qoa2/, y/ivvu/ yPAD     │
│  • No Python engine         │ link│  • z/ results local          │
└─────────────────────────────┘     └──────────────────────────────┘
```

The product **shows** BRAHL; the engine **runs** only where Python + browser exist.

---

## 2. Blockers (ordered by severity)

### B1 — No execution runtime on Base44

FoXYiZ is **Python + Selenium + Chrome/Edge**. Base44 apps typically run:

- Front-end SPA
- Serverless/edge functions for API
- Database entities

They do **not** provide:

- Long-lived Python processes
- Installed Chrome with `--headless`
- 30–120 second run windows for full suites

**Evidence:** qoa2 Issue plans document `/run` and `/analyze` as **404** — product routes for Run/Analyze were never wired to a backend runner (`PWeb_Issue_Run_404`, `PWeb_Issue_Analyze_404` in `y/qoa2/y1Plans.csv`).

### B2 — No job queue or run API

`BRAHL.py` and `fGUI.py` spawn subprocess:

```python
subprocess.Popen([sys.executable, str(engine), "--config", str(fstart_path)], ...)
```

qoa2 has no equivalent:

- No `POST /runs`
- No run ID, progress stream, or completion webhook
- No storage for `*_zResults.csv`, `*_zDash.html`, `brahl_report.md`

### B3 — yPAD and z/ are filesystem-local

Suites live at `KK/y/<suite>/`. Results at `KK/z/<timestamp>_<suite>/`.

Cloud product would need:

- Upload/sync yPAD to durable storage
- Worker writes results back
- Analyze tab reads from storage URLs, not `file://`

### B4 — Browser dependencies

`xActions.py` launches Chrome/Edge with options for cloud:

- Auto-detects EC2, Docker, `K_SERVICE`, etc.
- Sets `FOXYIZ_HEADLESS=true`
- Requires `--no-sandbox`, `--disable-dev-shm-usage` in containers

Base44 edge **cannot** satisfy this without an external worker.

### B5 — Secrets and .env

Engine loads `.env` for `yD_Secure.csv` placeholders (`fEngine2.py`). Cloud worker needs:

- Secret manager for test credentials
- Per-project env injection — not committed to repo

### B6 — MCP / agent path absent

Cursor agents today:

- Shell: `python f/fEngine2.py --config ...`
- Read `z/` directly
- Edit yPAD in workspace

Product customers need **HTTP/MCP** — no local `KK/` checkout.

---

## 3. What already helps (reuse, don’t rebuild)

| Capability | Location | Cloud use |
|------------|----------|-----------|
| Headless auto-detect | `x/xActions.py` | Worker container |
| BRAHL context/report | `f/fEngine2.py` | API calls same functions |
| zDash generation | `fEngine2.generate_dashboard` | Serve HTML from S3 |
| Run=Y shrink/restore | `BRAHL.py` logic | Port to API endpoints |
| Issue/A1 plan pattern | `Docs/BRAHL.md`, ivvu suite | Same yPAD in cloud store |

---

## 4. Recommended connection pattern

### Short term (proof)

1. Run **FastAPI** on developer machine (`localhost:8080`).
2. Expose via **ngrok** or Cloudflare tunnel.
3. Base44 **custom action** or external link: `POST https://tunnel/v1/runs`.
4. Validate qoa2 can trigger one smoke plan and display result URL.

### Production

| Layer | Technology (suggested) |
|-------|----------------------|
| API | FastAPI on Railway / Fly / ECS |
| Queue | Redis + RQ, or SQS |
| Worker | Docker: `python:3.12` + Google Chrome stable + `KK` clone |
| Storage | S3-compatible bucket — `ypad/{projectId}/`, `z/{runId}/` |
| Front | `qoa_web/web` on Vercel |
| MCP | `qoa_web/mcp` — stdio locally, SSE optional in cloud |

### qoa2.base44.app role

- **Keep:** marketplace, avatars, Jobs, Social, auth, billing
- **Delegate:** Run, Analyze, Loop execution UI → `qoa_web` or API
- **Integrate:** Loop page shows run history from FoXYiZ API; Build uploads yPAD to API

---

## 5. MCP vs API — when to use which

| Consumer | Channel | Why |
|----------|---------|-----|
| qoa_web browser | REST | Standard HTTP, auth, file upload |
| qoa2 Base44 | REST | Base44 functions call HTTP easily |
| Cursor agent | MCP | Native tool discovery; optional REST fallback |
| GitHub Actions | REST | `curl POST /runs` + poll |
| TestSprite-style IDE | MCP | Competitive parity (`QoA_Comps.md`) |

**Principle:** One implementation (Python service); MCP is a thin adapter over REST.

---

## 6. Desktop-first validation checklist

Before cloud deploy, prove locally:

- [ ] API starts run → `z/` folder appears with same structure as CLI
- [ ] Web UI shows progress lines from engine stdout
- [ ] zDash opens in browser from API URL
- [ ] Step 0 context JSON written with uploaded doc metadata
- [ ] MCP `foxyiz_run` returns run ID
- [ ] ivvu 44-plan Verify passes via API (not only CLI)
- [ ] Shrink/restore Run=Y changes y1Plans on disk/API store

---

## 7. Base44-specific research tasks

| # | Task | Owner | Output |
|---|------|-------|--------|
| R1 | Can Base44 backend call **external HTTPS** with secret API key? | Product | Yes/No + sample |
| R2 | Can Base44 **iframe** external origin (`qoa_web`)? | Product | CSP / auth pattern |
| R3 | File upload limits for yPAD CSV zip | Product | Max size, storage |
| R4 | User auth — share session with FoXYiZ API (JWT)? | Eng | SSO design |
| R5 | Spike Chrome in **Railway/Fly** Docker | Eng | Dockerfile + smoke log |

---

## 8. Conclusion

**qoa2 cannot run FoXYiZ internally** because Base44 is not a browser-automation host. The fix is not “patch qoa2” alone — it is **`qoa_web` + FoXYiZ Worker API**, with qoa2 as a **client** of that API.

Build and test the full path on **desktop (Cursor + local API + MCP)** first, then deploy the same API and worker to cloud so qoa2 and customers connect to one execution plane.

---

*See [PRD.md](./PRD.md) for product requirements and phased delivery.*
