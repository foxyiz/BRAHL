# qoa_web — Agent memory (read this first)

**Status:** BRAHL Arena over **FoXYiZ/** (`f` `x` `y` `z` `pyUtils`). **AI:** optional BYOK. **Run/Loop:** engine only.

**Spellings:** [Docs/terminology.md](../Docs/terminology.md) — **BRAHL** · **FoXYiZ** · **brawled** · yPAD · GO/NO-GO.

**App:** http://127.0.0.1:8765/welcome · **Arena:** `/app?demo=1` · **Admin:** `/admin`

**Today:** [../todaysummary.md](../todaysummary.md) · **Next:** [../NEXT.md](../NEXT.md) · **Handoff:** [Docs/HANDOFF.md](../Docs/HANDOFF.md)

---

## In scope

| Path | Purpose |
|------|---------|
| `qoa_web/web/` | Arena UI |
| `qoa_web/api/` | runner, projects, ypad, ai_* |
| `FoXYiZ/y/<suite>/` | Suites (thoughtstream, a77, Math, qoa_web_live, …) |
| `FoXYiZ/f/fStart/{suite}.json` | One fStart per app (+ optional `{suite}_deep.json` for tag lanes) |
| `FoXYiZ/pyUtils/` | cleaner (`--keep-latest`), orchestrate |
| `Docs/` | terminology · HANDOFF · BRAHL_PROMPT · rules |

## Out of scope

- `archive/**` · `FoXYiZ/f/fStart/archive/**` · bulk `FoXYiZ/z/**` in chat
- Fat journey CSVs in prompts · secrets / `.env`

---

## Commands

```powershell
cd c:\006\FXYZ\KK
python qoa_web/run_local.py
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream.json
python FoXYiZ\f\fEngine2.py --config f/fStart/thoughtstream_deep.json
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\pyUtils\cleaner.py --apply
```

Restart `run_local` after API/UI changes. Hard-refresh browser.

---

## Heal rules

- **Expected** = exact match; empty = presence only
- Apply never flips `Run` flags — Shrink/Restore does
- Heal one failing plan; re-smoke / re-deep that tag lane
- Never weaken **A1** (app defect) to force green

---

## Latest product gate (ThoughtStream)

- Deep **49/49** · BRAHL **GO** · Arena project `0935e530a120`
- Snapshot `y/thoughtstream/versions/*_v3-deep-regression`

---

## Docs map

| Doc | Use |
|-----|-----|
| [Docs/terminology.md](../Docs/terminology.md) | Shared vocabulary |
| [../NEXT.md](../NEXT.md) | Resume todos |
| [../todaysummary.md](../todaysummary.md) | Latest session |
| [Docs/HANDOFF.md](../Docs/HANDOFF.md) | Bootstrap |
| [Docs/BRAHL.md](../Docs/BRAHL.md) | Full BRAHL |
| [CHANGELOG.md](./CHANGELOG.md) | Versions |
