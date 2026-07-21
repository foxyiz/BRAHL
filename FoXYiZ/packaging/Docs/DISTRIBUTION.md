# Distribution — what to ship

## Answer: do you need `_internal`?

**Yes.** For this package, ship **`f\FoXYiZ.exe` together with `f\_internal\`**.

| Artifact | Alone? | Notes |
|----------|--------|-------|
| `FoXYiZ.exe` only | **No** | Bootloader only; missing Python + libs → will not start |
| `FoXYiZ.exe` + `_internal\` | **Yes** | Valid onedir PyInstaller runtime |
| Whole `FoXYiZ_user\` folder | **Preferred** | Includes fStart, x catalog, sample y, Docs |

Zip example:

```text
FoXYiZ_user.zip
  └── FoXYiZ_user\
        f\FoXYiZ.exe
        f\_internal\     ← required
        f\fStart\
        x\
        y\
        Docs\
        README.txt
```

## Why onedir (not one-file)?

- Faster cold start  
- Clear separation: editable `fStart` / `y` / `x` outside the freeze  
- `_internal` holds selenium, pandas, OpenSSL, etc.

A **one-file** `.exe` would embed `_internal` inside a single binary (slower extract-on-run). This packaging kit uses **onedir** intentionally.

## Do not ship

- `packaging/_build/` (scratch)  
- Source `f/fEngine2.py` (already frozen) unless you want architects to edit it  
- Secrets / `.env` with live keys  
- Large `z/` history (optional: empty `z/` is fine)

## Rebuild

From the FoXYiZ **source** tree (`KK/`):

```powershell
powershell -ExecutionPolicy Bypass -File FoXYiZ\packaging\build_exe.ps1
```

End users only need the resulting `dist\FoXYiZ_user\` folder.
