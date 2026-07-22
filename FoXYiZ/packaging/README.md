# FoXYiZ packaging

Build kit for the **end-user FoXYiZ package**. You do not need the rest of `KK/` to *use* the dist — only to *rebuild* the exe.

## Build (from `KK/`)

```powershell
powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
```

Output: `FoXYiZ/packaging/dist/FoXYiZ_user/`

## Smoke

```powershell
cd FoXYiZ\packaging\dist\FoXYiZ_user
.\f\FoXYiZ.exe --config f\fStart\Math.json
```

## Shipped docs (`_Docs/`)

Primary project docs only — see [Docs/README.md](Docs/README.md):

| Doc | Skill id | Audience |
|-----|----------|----------|
| [Docs/BRAHL.md](Docs/BRAHL.md) | `brahl` | Lifecycle |
| [Docs/FoXYiZ.md](Docs/FoXYiZ.md) | `foxyiz` | Engine + package |
| [Docs/QAonAir.md](Docs/QAonAir.md) | `qaonair` | Marketplace / Arena |

Deprecated generics: [Docs/_deprecated/](Docs/_deprecated/) (DISTRIBUTION, PACKAGING, USER_GUIDE, terminology).

## Layout reminder

```
FoXYiZ_user/
  f/FoXYiZ.exe + f/_internal/   ← both required
  f/fStart/  x/  y/  z/
  _pyUtils/                     ← only editable Python
  _Docs/                        ← BRAHL · FoXYiZ · QAonAir
  README.txt
```

Architects (source tree): `python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json`
