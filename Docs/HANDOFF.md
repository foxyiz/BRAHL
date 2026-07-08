# Handoff — new machine or new AI session

Use this when you copy `KK/` to another PC, zip a slice for a teammate, or open **Cursor / Claude / Copilot** on a fresh workspace.

**Principle:** Export **docs + active app + active suite**. Skip `z/` history and inactive `y/*` suites unless you need them.

---

## Minimum export bundle

Copy these paths relative to `KK/`:

```
Summary.md
Docs/                          # entire folder (this handoff layer)
qoa_web/
  MEMORY.md
  README.md
  qoa_userDoc.md
  DEPLOY.md
  run_local.py
  api/                           # FastAPI (invites, pricing, projects)
  web/                           # static UI (welcome, signin, app)
  mcp/                           # optional Cursor bridge
  data/                          # projects + invites seed
pyUtils/                       # utilities + zBatchDash.py
f/
  fEngine2.py
  fStart_qoa_web_verify.json
  fStart_qoa_web_smoke.json
  fStart_qoa_web_smoke_headless.json
  fStart_SCOPE.md
  requirements.txt
x/
  xActions.py
  xCapa.csv
  xCustom.py
y/qoa_web/                     # active yPAD only
z/
  zDash_template.html            # dashboard template only
.cursorignore                  # optional but recommended for agents
```

**Do not require in export:** `z/2026*` run folders, `archive/cleanup/`, `f/Foxyiz2.exe` (rebuild locally), inactive `y/qoa2/` etc.

---

## Bootstrap (new machine)

```powershell
cd <path-to-KK>

# Python 3.10+
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r qoa_web\api\requirements.txt
pip install -r f\requirements.txt

python qoa_web\run_local.py
# → http://127.0.0.1:8765/welcome
# Demo codes: QOA-CR5-001-001-DEMO · QOA-QH5-001-001-DEMO
# Arena: http://127.0.0.1:8765/app?demo=1
```

Verify FoXYiZ (server must be running):

```powershell
python u\reset_demo_data.py
python f\fEngine2.py --config f\fStart_qoa_web_verify.json
```

Expect **49/49** green on plans with `Run=Y` (tag **Verify**).

---

## Tell the AI what to read first

Paste or @-mention:

1. `Summary.md`
2. `Docs/README.md`
3. `qoa_web/MEMORY.md`
4. `Docs/BRAHL.md` (if doing verify/heal)
5. `Docs/FoXYiZ.md` (if editing yPAD)

**Task one-liner example:**

> We work on **qoa_web v1.3** only. Active suite is `y/qoa_web/`. Follow BRAHL loop in `Docs/BRAHL.md`. Do not edit `fEngine2.py` unless I ask. Run `python pyUtils/cleaner.py --apply` when done.

---

## Personas and yPAD sync

After editing `Docs/test-user-data/*.json`:

```powershell
python u\sync_personas.py
```

Regenerates persona columns in `y/qoa_web/y3Designs.csv` and `qoa_web/web/profiles.js`.

---

## Context files the app exposes

The **`.md`** button in qoa_web loads slim docs for in-app AI:

- `Docs/BRAHL_PROMPT.md`
- `Docs/FoXYiZ.md`
- `Docs/rules.md`
- `qoa_web/qoa_userDoc.md`

Keep those four aligned when product copy or verify scope changes.

---

## Where we left off (checklist)

Before closing a session, confirm:

- [ ] `python pyUtils/cleaner.py --apply` ran (ephemeral `z/` archived)
- [ ] `Summary.md` and `Docs/README.md` verify counts match `y/qoa_web/y1Plans.csv` (`Run=Y` + tag Verify)
- [ ] `qoa_web/MEMORY.md` status line updated if verify or scope changed
- [ ] No secrets in commits (`.env`, API keys)

Full ritual: [MAINTENANCE.md](./MAINTENANCE.md).
