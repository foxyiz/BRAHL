# x — capability catalog

`xCapa.csv` lists every **ActionType / ActionName** the engine can run.

When you author `y/<suite>/y2Actions.csv`, each row’s `ActionName` must match a row here (for example `xClick`, `xGetText`, `xGet`, `xTimeWait`).

| Column | Meaning |
|--------|---------|
| Module | Logical group (UI, API, Math, …) → maps to ActionType families like `xUI`, `xAPI` |
| Action | Exact `ActionName` used in y2 |
| Doc | Short description |
| Input | Expected `Input` shape |
| Output | Typical return / side effect |

## Examples

| y2 ActionType | ActionName | Input example |
|---------------|------------|---------------|
| xUI | xOpenBrowser | `edge` |
| xUI | xNavigate | `base_url` (from y3) |
| xUI | xGetText | `body_locator` |
| xUI | xClick | `btn_english` |
| xAPI | xGet | `api_host;ep_home` |
| xTime | xTimeWait | `3` |
| xReuse | *(plan id)* | reuse a `PReuse_*` plan |

Handlers themselves are **frozen inside** `f/FoXYiZ.exe` + `f/_internal/`.  
This folder is the **human/agent reference** — edit yPAD, not the binary, to change tests.

Full BRAHL authoring: see `Docs/BRAHL.md`.
