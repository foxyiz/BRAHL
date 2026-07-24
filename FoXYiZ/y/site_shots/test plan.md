# Test plan — site_shots (site screenshots)

App: https://jusdone.base44.app/

One plan per same-origin page: navigate → wait → `xCaptureImage` → body contains page-specific alive text.

## Regenerate

```powershell
python FoXYiZ\pyUtils\site_shot_author.py --base https://jusdone.base44.app/ --suite site_shots
python FoXYiZ\pyUtils\site_shot_author.py --base https://jusdone.base44.app/ --suite site_shots --crawl --max-pages 40
```

## Run

```powershell
$env:FOXYIZ_HEADLESS = "true"
python FoXYiZ\f\fEngine2.py --config f/fStart/site_shots.json
```

PNGs land under `z/<ts>_site_shots/` via Capture steps.

## Film roll / GIF

```powershell
python FoXYiZ\pyUtils\site_shot_roll.py --latest site_shots
# or: --run z/<ts>_site_shots --gif --filmstrip --delay-ms 900
```

Writes `<run>_roll.gif` and `<run>_filmstrip.png` into that run folder.
