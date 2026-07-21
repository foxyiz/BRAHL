# Test strategy — Ultimate Showdown

App: https://ultimate-clash-battle.base44.app/

## Scope
Guest + public UX for Ultimate Clash Battle (Who Would Win simulator):
home CTAs, game matchup corners, leaderboard filters, auth gates, about/contact/privacy.

## Risk
- Overlay modals (HOW TO PLAY / NEW FEATURES / ORACLE) intercept clicks
- Auth-gated Collection / Elo / Train redirect to login
- SPA route casing (`/game` vs `/Game`)

## Approach
Smoke = public pages + CTAs. UI = nav + tabs + guest continue. Manual = fight pick / oracle / challenge.
