# qoa_web — Agent memory (read this first)

**Status:** BRAHL Arena over **FoXYiZ/** (`f` `x` `y` `z` `pyUtils`). **AI:** optional BYOK. **Run/Loop:** engine only.

**App:** http://127.0.0.1:8765/welcome · **Arena:** `/app?demo=1` · **Admin:** `/admin`

**Today:** [../todaysummary.md](../todaysummary.md) · **Next session:** [../NEXT.md](../NEXT.md)

**Handoff:** [Docs/HANDOFF.md](../Docs/HANDOFF.md) · [FoXYiZ/f/fStart_SCOPE.md](../FoXYiZ/f/fStart_SCOPE.md)

---

## In scope

| Path | Purpose |
|------|---------|
| `qoa_web/web/` | Arena UI (`app.js`, `role-copy.js`, themes) |
| `qoa_web/api/` | main, runner (`RUN_PROFILES`), paths, projects, ypad, ai_* |
| `FoXYiZ/y/{Math,nalanda_app,qoa_web,qoa_web_live}/` | Suites (one folder = one project) |
| `FoXYiZ/f/fStart/{suite}.json` | **One fStart per app** (not per tag) |
| `FoXYiZ/pyUtils/` | orchestrate, cleaner, journey regen |

## Out of scope

- `archive/**` · `FoXYiZ/f/fStart/archive/**` · `FoXYiZ/z/**`
- Fat journey CSVs in chat · secrets / `.env`

---

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
```

Restart `run_local` after API/UI changes (`reload=False`). Hard-refresh browser.

---

## fStart model (2026-07-16)

- File: `f/fStart/{suite}.json` + required `capture`
- Arena: Run profiles Smoke→Manual · Threads · job overrides via `.runtime/`
- Engine: `thread_count>1` + 2+ tags → fan-out ([`fOrchestrate.py`](../FoXYiZ/pyUtils/fOrchestrate.py))

---

## Heal rules

- **Expected** = exact match; empty = presence only
- Apply never flips `Run` flags — Shrink/Restore does
- Heal one failing plan; re-smoke

---

## Docs

| Doc | Use |
|-----|-----|
| [../NEXT.md](../NEXT.md) | Resume todos |
| [../todaysummary.md](../todaysummary.md) | Latest session |
| [Docs/HANDOFF.md](../Docs/HANDOFF.md) | Bootstrap |
| [FoXYiZ/f/fStart_SCOPE.md](../FoXYiZ/f/fStart_SCOPE.md) | fStart + profiles |
| [Docs/BRAHL.md](../Docs/BRAHL.md) | Full BRAHL |
| [CHANGELOG.md](./CHANGELOG.md) | Versions |
