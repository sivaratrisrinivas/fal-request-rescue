# 04: Analyst UI inbox and detail

**What to build:** Readable case inbox and case detail showing timeline, evidence, diff, and approvals so an analyst can review and act without touching raw payloads.

**Blocked by:** 03 agent-flow-persistence.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 04). Backend: latest-disposition on list rows and
detail, `replay` flag from API, deterministic customer-draft endpoint.
Frontend: state-navigated inbox (endpoint, version, disposition) and detail
(timeline, evidence with digests, diagnosis, schema errors, field diff, draft
and packet preview, three approval controls, export, replay badge from flag).
Full suite 38/38, tsc clean, vite build ok, live click-path proven end to end
(list → detail → investigate → disposition → draft → approve → export, 4 audit
events). Review judgements: list N+1 disposition lookup fine at prototype
scale; frontend is one ~300-line file, split if 05 grows it.

- [ ] Inbox lists cases with endpoint, snapshot version, and disposition state
- [ ] Detail shows timeline, linked evidence, diagnosis with confidence and uncertainty, schema errors, field-level diff
- [ ] Proposed customer response and escalation export previewed before approval
- [ ] Explicit approval controls for correction, paid run, and customer text record actor and result
- [ ] Replay badge shown from API flag; synthetic incidents labeled; replay never presented as live
