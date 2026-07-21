# Today's summary — 2026-07-20 (production launch)

Spelling: **BRAHL** · **FoXYiZ**. Runbook: [Docs/PRODUCTION.md](Docs/PRODUCTION.md).

## Production launch implementation

- Commit **`4c82d18`** pushed to `origin/main` (foxyiz/BRAHL)
- Cloud FoXYiZ worker: Arena `runtime_mode=cloud` → HTTP worker on EC2
- `qoa_web/.env.production.example`, readiness + backup scripts
- Docs: PRODUCTION.md, terminology, DEPLOY EC2 contract filled
- Suites shipped: thoughtstream, ops_overview, a77, ultimate_showdown + versions

## Blocked on ops box

`brahl.qaonair.com` did not accept connections from this environment. After the host is up: set env secrets, Google, Stripe, EC2 worker, then re-smoke `/api/health`.

## Resume

[`NEXT.md`](NEXT.md) · [`todo.md`](todo.md)
