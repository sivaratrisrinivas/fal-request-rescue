# 05: Replay-complete plus capped live adapter

**What to build:** Complete obvious replay mode plus an opt-in live path with hard spend gates and timeout-safe retry behavior.

**Blocked by:** 04 analyst-ui.

**Status:** ready-for-agent

- [ ] Replay executes fixtures end-to-end with badge and fixture source; no credentials required
- [ ] Live adapter (server-side only) requires explicit approval plus per-session and per-day caps; one cheap permitted test records request ID, timestamps, status, cost estimate
- [ ] Client timeout with existing request ID checks status before any new run is suggested
- [ ] Retryable errors cite documented policy with attempt cap; non-retryable malformed input gets correction or escalation, no loop
- [ ] Missing request ID requests it; no lookup result fabricated
