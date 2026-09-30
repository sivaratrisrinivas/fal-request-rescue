# 05: Replay-complete plus capped live adapter

**What to build:** Complete obvious replay mode plus an opt-in live path with hard spend gates and timeout-safe retry behavior.

**Blocked by:** 04 analyst-ui.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 05). New: `policy` retry classifier (retryable
with cap 3, else correct-or-escalate), `fal_live` server-side queue adapter
(key in env only, never logged), replay route (no credentials, cites origin),
request-status route (mock-labeled without key, never fabricated), live-test
`mode=live` with pending-status guard (409), key gate (503), then existing
caps and approvals. UI gained replay run + live test controls. Full suite
46/46, tsc/build clean, live E2E proven for replay, 409, 503, mock status.
Live submit itself is code-complete but unproven against real fal — no key was
available; adapter transport is mocked in tests. `replay: true` in detail is
still constant; 06/07 can flip it per-action once live runs exist.

Update 2026-10-01: fal queue adapter swapped for a local Ollama runner
(free, open-source, no key, $0; see ADR-0003). Same gates, same record shape,
cost 0.0. Request-status now reads recorded runs first, labeled mock otherwise.

Update 2026-10-01 (later): Ollama dropped for OpenRouter's free tier (see
ADR-0004) — the key was already held, quota is real (50/day, enforced in
code), and generation IDs come back real. Same gates plus quota, same record
shape, cost 0.0.

- [ ] Replay executes fixtures end-to-end with badge and fixture source; no credentials required
- [ ] Live adapter (server-side only) requires explicit approval plus per-session and per-day caps; one cheap permitted test records request ID, timestamps, status, cost estimate
- [ ] Client timeout with existing request ID checks status before any new run is suggested
- [ ] Retryable errors cite documented policy with attempt cap; non-retryable malformed input gets correction or escalation, no loop
- [ ] Missing request ID requests it; no lookup result fabricated
