# FoXYiZ packaging

Self-contained build + ship kit for the **end-user FoXYiZ package**.  
You do not need the rest of `KK/` to *use* the dist — only to *rebuild* the exe.

## What you get

```
packaging/
  README.md              ← this file
  FoXYiZ.spec            ← PyInstaller onedir spec
  build_exe.ps1          ← build + assemble
  Docs/                  ← shipped into dist/FoXYiZ_user/Docs/
  dist/FoXYiZ_user/      ← ship this folder (gitignored build output)
    f/FoXYiZ.exe
    f/_internal/         ← REQUIRED next to the exe
    f/fStart/
    x/xCapa.csv
    y/Math/
    z/
    Docs/
    README.txt
```

## Build (from `KK/`)

```powershell
powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
```

Output: `FoXYiZ/packaging/dist/FoXYiZ_user/`

## Smoke the package

```powershell
cd FoXYiZ\packaging\dist\FoXYiZ_user
.\f\FoXYiZ.exe --config f\fStart\Math.json
```

## Formula

```
f(x, y) = z
```

| Folder | Role in the package |
|--------|---------------------|
| **f/** | Engine (`FoXYiZ.exe` + `_internal`) and **fStart** run configs |
| **x/** | Capability catalog (`xCapa.csv`) — reference for authoring actions |
| **y/** | Editable yPAD suites (plans / actions / designs) |
| **z/** | Run results (`*_zResults.csv`, `*_zDash.html`, `brahl_report.md`) |

## `_internal` vs exe alone

**You need both.** This is a PyInstaller **onedir** build:

| Piece | What it is |
|-------|------------|
| `f/FoXYiZ.exe` | Thin bootloader (~20 MB) |
| `f/_internal/` | Python runtime + selenium, pandas, etc. (~100+ MB) |

Shipping **only** `FoXYiZ.exe` will fail at launch. Zip/ship the whole `FoXYiZ_user` folder.

See [Docs/DISTRIBUTION.md](Docs/DISTRIBUTION.md).

## Docs in this folder

| File | Purpose |
|------|---------|
| [Docs/USER_GUIDE.md](Docs/USER_GUIDE.md) | How end users run and author suites |
| [Docs/BRAHL.md](Docs/BRAHL.md) | Build → Run → Analyze → Heal → Loop |
| [Docs/terminology.md](Docs/terminology.md) | FoXYiZ / BRAHL / yPAD spellings |
| [Docs/DISTRIBUTION.md](Docs/DISTRIBUTION.md) | What to ship / not ship |
| [Docs/x_README.md](Docs/x_README.md) | How to use `xCapa.csv` |

## Architects (full source)

Keep using the repo tree:

```powershell
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
```
