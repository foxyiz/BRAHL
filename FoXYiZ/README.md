# FoXYiZ

Engine for **`f(x, y) = z`** — BRAHL Arena backend.

**Guide:** [FoXYiZ_Readme.md](./FoXYiZ_Readme.md)

```
FoXYiZ/
  f/         fEngine2.py · fStart/{suite}.json · fStart_SCOPE.md
  x/         actions
  y/         yPAD suites (one folder = one app)
  z/         run output (gitignored / Cursor-excluded)
  pyUtils/   fOrchestrate, cleaner, journey regen
```

```powershell
# From KK/
python FoXYiZ\f\fEngine2.py --config f/fStart/Math.json
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
python FoXYiZ\pyUtils\cleaner.py
```

Arena: [../qoa_web/README.md](../qoa_web/README.md) · memory: [../qoa_web/MEMORY.md](../qoa_web/MEMORY.md) · resume: [../NEXT.md](../NEXT.md)
