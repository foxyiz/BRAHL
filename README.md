Desktop BRAHL

Lean desktop tool for the QA hunter: FoXYiZ runs tests, BRAHL decides Go/No-Go.

**BRAHL** is local-only.

## Quick start

```powershell
cd c:\Path\To\BRAHL
python qoa_web\run_local.py
```

Open http://127.0.0.1:8766.

1. Bind your **app under test** — GitHub URL (clone into `workspaces/`) or a local folder path.
2. Build → pick/create a challenge (yPAD under `FoXYiZ/y/`).
3. Run → Analyze → Heal → Loop → BRAHL.

## Layout

```
BRAHL/
  FoXYiZ/          engine f, x, y (Math, site_shots, a77), empty z/, pyUtils
  qoa_web/         slim Arena (no Account/Role/Wallet/Admin)
  workspaces/      cloned GitHub repos
  Docs/            BRAHL_DESKTOP_BYOK.md
```

## AI (BYOK)

Set `OPENAI_API_KEY` in `FoXYiZ/f/.env` (see `.env.example`). Toggle **AI on/off** in the top bar when a project is selected.

## Workspace API

- `GET /api/workspace` — current bind
- `POST /api/workspace` — `{ "source":"github", "repo_url":"…" }` or `{ "source":"local", "local_path":"…" }`
- `DELETE /api/workspace` — clear bind
