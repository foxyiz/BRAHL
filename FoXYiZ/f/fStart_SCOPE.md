# fStart configs — one JSON per app

**Canonical layout:** `f/fStart/{suite}.json` (e.g. `qoa_web_live.json`, `Math.json`).  
Per-tag clones live in `f/fStart/archive/` for reference only.

## Arena Run (preferred)

1. Select project / suite in the top bar.
2. One **fStart** chip appears (`f/fStart/{suite}.json`).
3. Select **Run profiles** (fixed order): Smoke → UI → API → Performance → Security → Manual.
4. Set **Threads**:
   - `1` → OR filter (all expanded tags from selected profiles, one engine process)
   - `>1` + 2+ profiles → **parallel by profile** (one worker per profile)
5. Click **Run**.

`POST /api/jobs` accepts `profiles`, `thread_count`, and optional `tags`.

### Profile → tags → file set

| Profile | yPAD tags (OR) | Suite files |
|---------|----------------|-------------|
| **Smoke** | `Smoke` | Gate only (`*_verify_gate.json` or non-journey CSVs) |
| **UI** | Nav, Build, Panel, Heal, Loop, Analyze, BRAHL, Shell, Landing, Atomic77, Cost, Run | Journey CSVs when present |
| **API** | `API` | Journey CSVs when present |
| **Performance** | `Performance` | Journey CSVs when present |
| **Security** | `Security` | Journey CSVs when present |
| **Manual** | `Manual` | Full suite JSON |

UI/API replace archived `fStart/*_journey_*.json` clones. Mapping lives in `qoa_web/api/runner.py` (`RUN_PROFILES`, `PROFILE_SUITE_MODE`).

## Tag fan-out vs OR filter (engine)

| `thread_count` | `tags` / profiles | Behavior |
|----------------|-------------------|----------|
| `1` | 1+ tags | **OR** filter — classic FoXYiZ |
| `>1` | 2+ tags, one suite | **Tag fan-out** via [`pyUtils/fOrchestrate.py`](../pyUtils/fOrchestrate.py) |
| Arena: `>1` + 2+ **profiles** | — | One runtime fStart per profile, parallel batch |

## Screen capture (required)

Every fStart should include:

```json
"capture": {
  "image": "on_fail",
  "video": "off",
  "video_fps": 2,
  "subdir": ""
}
```

| Field | Values | Meaning |
|-------|--------|---------|
| `image` | `off` · `on_fail` · `every_step` · `on_pass` | Auto PNG after UI steps |
| `video` | `off` · `on_fail` · `every_step` · `plan` | Frame sequence |
| `video_fps` | 1–10 | Frames per second |
| `subdir` | e.g. `captures` | Folder under plan `z/` dir |

## CLI smoke

```powershell
cd c:\006\FXYZ\KK
python FoXYiZ\f\fEngine2.py --config f/fStart/qoa_web_live.json
```

Arena Smoke profile writes `f/fStart/.runtime/*.json` (gate suite + Smoke tag).

## Archive

Older journey/smoke/verify clone JSONs: `FoXYiZ/f/fStart/archive/`. Do not use them for new runs.
