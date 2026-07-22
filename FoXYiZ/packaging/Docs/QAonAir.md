---
name: qaonair
description: >-
  QA on Air marketplace and BRAHL Web Arena framing for FoXYiZ packages. Use when
  explaining Creators vs Hunters, Arena phases, wallets, personas, or how the
  product sits on FoXYiZ. Trigger on QAonAir, QA on Air, Arena, qoa_web,
  Champion, Contender, wallet, invite, brahl.qaonair.com.
---

# QA on Air — marketplace & Arena

**QA on Air** is the product brand: Creators post challenges, QA Hunters deliver evidence, and **BRAHL** + **FoXYiZ** automate to a clear **GO / NO-GO**.

Tagline: **You Build, We QA — let's BRAHL!**

This package is the **FoXYiZ referee** you can run offline. Arena (`qoa_web`) is the optional web UI over the same `y/` · `z/` model.

## Skill

| Field | Value |
|-------|-------|
| **Skill id** | `qaonair` |
| **Primary users** | Creator, QA Hunter, Admin, Promoter; product/GTM agents |
| **Apply when** | Explaining marketplace roles, Arena tabs, invites, wallets, demo personas |
| **Do not use for** | Writing yPAD steps or exe flags → [FoXYiZ.md](FoXYiZ.md); T1–T3 heal protocol → [BRAHL.md](BRAHL.md) |
| **Related skills** | `brahl` (lifecycle) · `foxyiz` (engine/package) |
| **Triggers** | QAonAir, QA on Air, Arena, qoa_web, Champion, Contender, wallet, invite, Nalanda |

---

## Layers

| Layer | What it is | What users see |
|-------|------------|----------------|
| **QA on Air** | Marketplace + ecosystem brand | Creators ↔ Hunters, wallets, invites |
| **BRAHL** | Quality lifecycle name | Build / Run / Analyze / Heal / Loop / report |
| **Arena (BRAHL Web)** | `qoa_web` FastAPI + browser UI | Tabs over local or hosted API |
| **FoXYiZ** | LCNC automation engine | Invisible referee on Run / Loop |

Mental model: **FoXYiZ = referee · BRAHL report = scorecard · Arena = control room**.

---

## Personas

| UI label | Job |
|----------|-----|
| **Creator** | Post challenge, fund QA wallet, BRAHL to GO/NO-GO |
| **QA Hunter** | Hunt bugs, attach evidence, get paid |
| **Nalanda** | Learn / teach — no BRAHL phases |
| **Promoter** | Invite / referral path |
| **Admin** | Ecosystem stats, invite batches |

Arena metaphor: Creator = Champion · Hunter = Contender · FoXYiZ = referee.

Demo personas **P1–P9** map to y3 **D1–D9** in full KK source (not required to run this exe package).

---

## Arena phases ↔ this package

| Arena tab | Uses FoXYiZ? | In this zip |
|-----------|--------------|-------------|
| Build | yPAD on disk | Edit `y/` + `f/fStart/` |
| Run / Loop | **Yes — exe** | `.\f\FoXYiZ.exe --config …` |
| Analyze / Heal | Reads/writes `z/` · `y/` | Open `z/`; heal CSVs; optional `_pyUtils` |
| BRAHL | Report | `brahl_report.md` after Verify |
| $ / Nalanda | Wallet / community | Product-only (hosted Arena) |

Local Arena (full KK): `http://127.0.0.1:8765` · hosted target: `https://brahl.qaonair.com`.

**Hard rule:** Run and Loop are FoXYiZ only — never the LLM.

---

## How Arena talks to FoXYiZ (architecture)

```
Browser (Arena)
  → FastAPI (qoa_web/api)
    → FoXYiZ.exe / fEngine2  +  fStart  +  yPAD
      → z/<run>/  (zResults, zDash, zlogs, brahl_report)
```

This **distributable** skips Arena: you drive BRAHL from the shell and `_Docs`.

---

## See also

- [BRAHL.md](BRAHL.md) — lifecycle skill  
- [FoXYiZ.md](FoXYiZ.md) — package / exe skill  
- [README.md](README.md) — skill map  
