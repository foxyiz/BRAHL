# FoXYiZ

Engine package for **`f(x, y) = z`** — used by the BRAHL Arena (`qoa_web`) as the automation backend.

**Full guide (skills · memory · yPAD efficiency · AI rules):**  
**[FoXYiZ_Readme.md](./FoXYiZ_Readme.md)** ← start here.

```
FoXYiZ/
  f/         engine (fEngine2.py, fStart_*.json, fOrchestrate.py)
  x/         actions
  y/         yPAD suites
  z/         run output (excluded from Cursor index)
  pyUtils/   maintenance scripts
  FoXYiZ_Readme.md   consolidated operator + AI guide
```

```powershell
# From KK/
python FoXYiZ\f\fEngine2.py --config f\fStart_Math.json
python FoXYiZ\pyUtils\cleaner.py
```

Arena: [../qoa_web/README.md](../qoa_web/README.md) · memory: [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md).
