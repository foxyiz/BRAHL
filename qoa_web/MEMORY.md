# qoa_web v1.4 — Agent memory (read this first)

**Status:** desktop BRAHL UI over **FoXYiZ/** (`f` `x` `y` `z` `pyUtils`). **AI:** optional BYOK. **Run/Loop:** engine only.

**App:** http://127.0.0.1:8765/welcome · **Arena:** `/app` · **Admin:** `/admin`

**Today:** [../todaysummary.md](../todaysummary.md) · **AI cost:** `Docs/BRAHL_DESKTOP_BYOK.md` · meter: `qoa_web/data/ai_usage.json`

**Handoff:** [Docs/HANDOFF.md](../Docs/HANDOFF.md) · [FoXYiZ/FoXYiZ_Readme.md](../FoXYiZ/FoXYiZ_Readme.md) · [Docs/README.md](../Docs/README.md)

---

## In scope (only touch these unless user says otherwise)

| Path | Purpose |
|------|---------|
| `qoa_web/web/` | index, app.js, admin, welcome, signin, themes |
| `qoa_web/api/` | main, runner, paths (`FOXYIZ_ROOT`), projects, ypad, suite_docs, ai_*, admin_* |
| `FoXYiZ/y/Math/`, `FoXYiZ/y/nalanda_app/` | Lean suites for Loop/Verify/Heal |
| `FoXYiZ/f/fStart_Math.json`, `…nalanda…` | Primary smoke configs |
| `FoXYiZ/pyUtils/` | cleaner, persona sync, zBatchDash |

## Out of scope

- `archive/**` — never add to context
- `FoXYiZ/z/**` — zResults / zDash / artifacts (huge)
- Fat journey CSVs pasted into chat
- `qoa_web/data/projects.json` unless seed-data work

---

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
# Arena bypass: /app?demo=1

python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
python FoXYiZ\pyUtils\cleaner.py --apply
```

Restart server after API/UI changes.

---

## Avatars

**Creator** · **QA Hunter** · **Nalanda** — [qoa_userDoc.md](./qoa_userDoc.md). Personas: [Docs/test-user-data/](../Docs/test-user-data/).

---

## FoXYiZ heal rules

- **Expected** = exact string match; empty = presence only
- No `xWaitFor` — use xGetText/xClick/xNavigate
- After `xReuse`, parent plan must navigate (base_url or profile_url)
- Heal one failing plan at a time; re-run lean smoke

---

## Docs (lean)

| Doc | Use |
|-----|-----|
| [../todaysummary.md](../todaysummary.md) | Today's key changes |
| [Docs/HANDOFF.md](../Docs/HANDOFF.md) | Bootstrap |
| [Docs/DEPLOY.md](../Docs/DEPLOY.md) | VPS / launch checklist |
| [Docs/BRAHL.md](../Docs/BRAHL.md) | Full BRAHL |
| [qoa_userDoc.md](./qoa_userDoc.md) | Users & arenas |
| [CHANGELOG.md](./CHANGELOG.md) | Version history |
