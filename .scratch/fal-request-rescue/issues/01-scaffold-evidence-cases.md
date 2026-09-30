# 01: Scaffold plus evidence and cases foundation

**What to build:** Runnable repo with case JSON format, redaction, pinned schemas, and seed synthetic cases so investigation has grounded inputs.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 01). Backend pytest 6/6, Bun build ok, live uvicorn
smoke ok (health + create). Review: no repo standards docs exist, so baseline only.
One judgement call — redaction block duplicated in POST /cases and POST /cases/import;
extract on next touch (02). Note: fixture queue_events/webhook fields import cleanly
but are not yet persisted as evidence rows; that lands in 02/03 with state parsing.

- [ ] Backend, frontend toolchain (Bun), and SQLite store run locally with case create/import/list behavior
- [ ] Redact function strips keys/passwords/credentials before save and before model send
- [ ] Three endpoint schema snapshots plus pricing references pinned with versions cited
- [ ] Ten synthetic cases with gold dispositions and evidence references import cleanly
- [ ] Case export as JSON round-trips for replay
