# _Docs — FoXYiZ package documentation

Primary project docs only. Generic packaging / distribution guides are **deprecated**.

| Document | Project | Audience |
|----------|---------|----------|
| [BRAHL.md](BRAHL.md) | Lifecycle | Creators, Hunters, agents running Build→Verify |
| [FoXYiZ.md](FoXYiZ.md) | Engine + this package | Operators authoring yPAD and running `FoXYiZ.exe` |
| [QAonAir.md](QAonAir.md) | Marketplace / Arena | Product users of QA on Air + BRAHL Web |

## Skill map

| Skill id | Owns | Primary doc | Users |
|----------|------|-------------|-------|
| `brahl` | Build → Run → Analyze → Heal → Loop → Verify → report | [BRAHL.md](BRAHL.md) | Creator, QA Hunter, agents |
| `foxyiz` | `f(x,y)=z`, yPAD, fStart, exe, `z/`, `_pyUtils` | [FoXYiZ.md](FoXYiZ.md) | Operators, architects, agents |
| `qaonair` | Marketplace, Arena tabs, wallets, personas | [QAonAir.md](QAonAir.md) | Creator, Hunter, Admin, agents |

Each primary doc has a standardized **Skill** section (id, users, triggers, related).

## Deprecated (do not extend)

Moved under [`_deprecated/`](_deprecated/README.md):

- `DISTRIBUTION.md` → see **FoXYiZ.md** (ship layout / `_internal`)
- `PACKAGING.md` → see **FoXYiZ.md** (rebuild note for architects)
- `USER_GUIDE.md` → see **FoXYiZ.md** (quick start / authoring)
- `terminology.md` → spellings live in each primary + **FoXYiZ.md** glossary

## Package root

```
FoXYiZ_user/
  f/FoXYiZ.exe + f/_internal/   ← Run (no engine source)
  f/fStart/  x/  y/  z/
  _pyUtils/                     ← only editable Python (optional Analyze helpers)
  _Docs/                        ← this folder
  README.txt
```
