# 08: Proof cards plus closing beat

**What to build:** Case detail reads like the prototype: findings as proof
cards (what was seen, where, how sure — no digests, kinds, or IDs on screen),
investigation auto-runs on open, and approval lands a closing beat
("Fixed — reply drafted", "Waiting on customer", "With engineering").
Allowed values render as chips, not Python repr.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

## Comments

Implemented 2026-10-01 (ticket 08). Backend: `GET /cases/{id}/disposition`
returns the persisted doc, so opening a case reads instead of re-POSTing (no
audit spam). Frontend: proof cards with human sources, auto-investigate on
open, one big decision button per answer, closing beat after approval, allowed
values as chips, drill-down timeline/export, deep-linkable `#case-<id>`.
Full suite 61/61, tsc clean, build ok, all three answer states screenshotted
against the real API. Known gap: closing beat verified by code path only
(headless run cannot click); no "run answer" button, digests, or IDs on screen.

- [ ] Findings render as proof cards with no machine vocabulary on screen
- [ ] Opening a case runs investigation without a manual run action
- [ ] Approval shows the closing beat for the disposition
- [ ] Allowed values display as chips
- [ ] No "run disposition" button, no on-screen digests or evidence IDs
