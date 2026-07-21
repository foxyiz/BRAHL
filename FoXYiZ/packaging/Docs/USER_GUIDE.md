# FoXYiZ user guide (packaged)

You have a **standalone FoXYiZ folder**. No Python install required to run suites.

## Quick start

From the package root (`FoXYiZ_user/`):

```powershell
.\f\FoXYiZ.exe --config f\fStart\Math.json
```

Bare run (uses `f\fStart\default.json` → Math Smoke):

```powershell
.\f\FoXYiZ.exe
```

Results land in `z\<timestamp>_<suite>\`.

## Layout

```
FoXYiZ_user/
  f/
    FoXYiZ.exe       engine
    _internal\       REQUIRED runtime (keep beside the exe)
    fStart\          run configs (JSON)
  x/
    xCapa.csv        action catalog (what ActionName values exist)
    README.md
  y/
    Math\            sample suite (y1 / y2 / y3 + suite JSON)
  z\                 results (auto-created)
  Docs\              BRAHL + terminology + this guide
  README.txt         short cheatsheet
```

## Add a suite

1. Copy `y\Math\` → `y\<mysuite>\`
2. Edit `y1Plans.csv`, `y2Actions.csv`, `y3Designs.csv`, and `<mysuite>.json`
3. Add `f\fStart\<mysuite>.json` pointing at `y/<mysuite>/<mysuite>.json`
4. Run:

```powershell
.\f\FoXYiZ.exe --config f\fStart\<mysuite>.json
```

Use **`x\xCapa.csv`** to pick valid `ActionType` / `ActionName` pairs for y2.

## fStart JSON (minimal)

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

`tags` filters which `Run=Y` plans execute.

## BRAHL (short)

1. **Build** — write yPAD CSVs  
2. **Run** — `FoXYiZ.exe --config …`  
3. **Analyze** — open `z\…\*_zResults.csv` / `*_zDash.html`  
4. **Heal** — fix yPAD (T1–T3); document A1 app bugs without weakening asserts  
5. **Loop** → **Verify** → write Go/No-Go in `brahl_report.md`

Full detail: [BRAHL.md](BRAHL.md) · [terminology.md](terminology.md)

## Do not

- Delete or relocate `f\_internal\` without the exe  
- Ship only `FoXYiZ.exe`  
- Commit secrets into `y3Designs.csv` (use a local `.env` beside the package if needed)
