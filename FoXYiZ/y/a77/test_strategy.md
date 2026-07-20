# Test strategy — Atomic 77 (a77) v4 guest-arch

App: https://a77.base44.app/ (researched 2026-07-20)

## Architecture change vs v3
- **Guest demo shell**: `/dashboard`, BRAHL phases (`/build`…`/brahl`), `/content`, `/seo`, `/scheduler` open **without login** (Guest chip + Summit Realty demo).
- Landing CTAs (**Get Started Free** / Enter App) go to **/dashboard** (guest), not `/register`.
- `/login` + `/register` remain for account creation; ThoughtStream capture iframe still asks Sign in.
- Legacy `/social-scheduler` still 404; real scheduler is `/scheduler`.

## Automation vs HITL
Guest Smoke/UI covers landing + guest product shell + auth forms + 404.
Persisted account flows (OAuth, save captures, paid checkout) stay Manual.
