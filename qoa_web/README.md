# qoa_web — BRAHL Web App v1.0

Local BRAHL web UI + FoXYiZ API. **Handoff context:** [Summary.md](../Summary.md).

Open **http://127.0.0.1:8765** · `python qoa_web/run_local.py` from `KK/`.

## Quick test

```powershell
python qoa_web/run_local.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json   # 50 plans, server required
```

**Latest verify:** **60/60** — `z/20260703_155434_qoa_web/` (Client + HITL)

## MCP (Cursor agents)

```powershell
python qoa_web/mcp/server.py
```

Tools: `foxyiz_run`, `foxyiz_run_status`, `foxyiz_analyze`, `foxyiz_list_runs` (calls local API).

## Detail docs

| Doc | Purpose |
|-----|---------|
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
| [AVATARS_AND_BUILD.md](./AVATARS_AND_BUILD.md) | Client / HITL, Build, BRAHL tab, APIs |
| [PRD.md](./PRD.md) | Product + cloud architecture |
| [RESEARCH.md](./RESEARCH.md) | qoa2 vs local engine gap |
