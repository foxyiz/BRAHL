---
name: foxyiz
description: >-
  FoXYiZ packaged engine f(x,y)=z. Use when running FoXYiZ.exe, authoring yPAD
  (y1/y2/y3), editing fStart, reading z/ or zlogs, using _pyUtils helpers, or
  explaining package layout (_internal, xCapa). Trigger on FoXYiZ, foxyiz, yPAD,
  fStart, zResults, zDash, zlogs, xCapa, FoXYiZ.exe, _pyUtils.
---

# FoXYiZ — engine & package

Automation engine for this distributable. **No** shippable `fEngine2.py` / `xActions.py` — Run is **`f\FoXYiZ.exe`**.

Spellings: **FoXYiZ** · **yPAD** · **fStart** · **zlogs**.

## Skill

| Field | Value |
|-------|-------|
| **Skill id** | `foxyiz` |
| **Primary users** | Operators, suite authors, architects (rebuild), agents editing yPAD only |
| **Apply when** | Running the exe; authoring suites; reading `z/`; using `_pyUtils`; ship/layout questions |
| **Do not use for** | Marketplace wallets / Arena UI tabs → [QAonAir.md](QAonAir.md); lifecycle triage policy → [BRAHL.md](BRAHL.md) |
| **Related skills** | `brahl` (lifecycle) · `qaonair` (product) |
| **Triggers** | FoXYiZ, foxyiz, yPAD, fStart, zResults, zDash, zlogs, xCapa, `_internal`, `_pyUtils` |

**Agent default:** edit **yPAD + fStart + `_Docs`** only. Do not modify `f\_internal\` or the exe unless the user explicitly asks.

---

## Formula

```
f(x, y) = z
```

| Folder | Role |
|--------|------|
| **f/** | `FoXYiZ.exe` + **`_internal/` (required)** + `fStart/` |
| **x/** | `xCapa.csv` — ActionName catalog for y2 |
| **y/** | Editable yPAD suites |
| **z/** | Results (`*_zResults.csv`, `*_zDash.html`, `zlogs.txt`, reports) |
| **_pyUtils/** | Only editable Python in the package (Analyze helpers; needs Python) |
| **_Docs/** | BRAHL · FoXYiZ · QAonAir |

---

## Quick start

From the package root:

```powershell
.\f\FoXYiZ.exe --config f\fStart\Math.json
```

Bare run → `f\fStart\default.json` (Math Smoke):

```powershell
.\f\FoXYiZ.exe
```

Results: `z\<timestamp>_<suite>\` including **`zlogs.txt`**. Flat index: `z\zlogs.txt`.

### fStart (minimal)

```json
{
  "configs": ["y/Math/Math.json"],
  "thread_count": 1,
  "timeout": 6,
  "headless": true,
  "debug": false,
  "tags": ["Smoke"],
  "capture": { "image": "on_fail", "video": "off", "video_fps": 2, "subdir": "" }
}
```

### Add a suite

1. Copy `y\Math\` → `y\<mysuite>\`
2. Edit y1 / y2 / y3 + `<mysuite>.json`
3. Add `f\fStart\<mysuite>.json`
4. Run with `--config f\fStart\<mysuite>.json`

Use **`x\xCapa.csv`** for valid `ActionType` / `ActionName` pairs.

---

## Ship layout (was DISTRIBUTION)

**You need both** `f\FoXYiZ.exe` and `f\_internal\` (PyInstaller onedir). Shipping the exe alone will not start.

Zip the whole `FoXYiZ_user` folder:

```text
FoXYiZ_user\
  f\FoXYiZ.exe
  f\_internal\      ← required
  f\fStart\
  x\
  y\
  z\
  _pyUtils\         ← optional Analyze helpers
  _Docs\
  README.txt
```

**Not shipped as source:** `fEngine2.py`, `xActions.py` (frozen inside `_internal` only).

### `_pyUtils` (editable Python only)

| Script | Role |
|--------|------|
| `_paths.py` | Package paths |
| `cleaner.py` | Archive old `z/` (dry-run default) |
| `yVisualizer.py` | yPAD map HTML |
| `zDefects.py` | Failure rollup HTML |
| `zBatchDash.py` | Multi-run batch dashboard |

```powershell
python _pyUtils\cleaner.py
python _pyUtils\yVisualizer.py
python _pyUtils\zDefects.py
python _pyUtils\zBatchDash.py --name mybatch --since 20260721
```

### Glossary

| Term | Meaning |
|------|---------|
| **yPAD** | y1Plans · y2Actions · y3Designs |
| **fStart** | `f/fStart/{suite}.json` |
| **zlogs.txt** | Per-run console transcript (+ flat `z/zlogs.txt`) |
| **brawl** | Full BRAHL cycle to Verify |
| **smoke** / **deep** | Shell only vs expanded tags |

### Rebuild (architects — was PACKAGING)

From KK source tree (not needed for end users):

```powershell
powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
```

---

## Do not

- Delete or move `f\_internal\` without the exe  
- Ship only `FoXYiZ.exe`  
- Put secrets in `y3Designs.csv`  

## See also

- [BRAHL.md](BRAHL.md) — lifecycle, failure classes, report  
- [QAonAir.md](QAonAir.md) — Arena / marketplace  
- [README.md](README.md) — doc index + skill map  
