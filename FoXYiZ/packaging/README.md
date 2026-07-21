# FoXYiZ.exe packaging

Builds an **end-user** onedir package: engine binary + editable `fStart/` + sample `y/Math/`.

## Build

From **`KK/`**:

```powershell
powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
```

Output: `FoXYiZ/packaging/dist/FoXYiZ_user/`

## What’s inside the exe

| Bundled | Editable beside exe |
|---------|---------------------|
| `fEngine2.py` (entry) | `fStart/*.json` |
| `x/xActions.py`, `xCapa.csv` | `y/<suite>/` CSVs |
| `pyUtils`: `_paths`, `fOrchestrate`, `xCustom`, `zBatchDash` | `z/` results |

Architects keep using full source: `python FoXYiZ\f\fEngine2.py --config …`

## Smoke

```powershell
cd FoXYiZ\packaging\dist\FoXYiZ_user
.\FoXYiZ.exe --config fStart\Math.json
```
