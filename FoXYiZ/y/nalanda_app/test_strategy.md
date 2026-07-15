# Test strategy — nalanda_app

## Purpose

Test plan for Nalanda SkillFlow AI launch readiness focusing on core routes and UX validation.

## App under test

https://nalanda.base44.app/

## Approach

- **Automated** — FoXYiZ runs yPAD plans marked `Run=Y` (engine only; no LLM required).
- **Manual** — QA Hunters cover `Run=N` UX, real-device, and exploratory gaps.
- **AI (optional)** — assists Build / Analyze / Heal when AI is on; never replaces FoXYiZ Run.

## Coverage posture

- **8** automated · **4** manual · **12** plans in scope (from yPAD / BRAHL draft).

## BRAHL QA agent cycle

1. **Build** — strategy, test plan, and yPAD (plans · steps · data).
2. **Run** — FoXYiZ executes automated plans.
3. **Analyze** — failures from `z/` (Input · Expected · Output).
4. **Heal** — fix yPAD locators / steps / data.
5. **Loop** — retry fails (up to 3×) · optional full Verify.
6. **BRAHL** — Go/No-Go launch report.

_Source: `y/nalanda_app/test_strategy.md` (synthesized if the file was missing)._