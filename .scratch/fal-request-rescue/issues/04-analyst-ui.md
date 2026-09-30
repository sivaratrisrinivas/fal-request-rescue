# 04: Analyst UI inbox and detail

**What to build:** Readable case inbox and case detail showing timeline, evidence, diff, and approvals so an analyst can review and act without touching raw payloads.

**Blocked by:** 03 agent-flow-persistence.

**Status:** ready-for-agent

- [ ] Inbox lists cases with endpoint, snapshot version, and disposition state
- [ ] Detail shows timeline, linked evidence, diagnosis with confidence and uncertainty, schema errors, field-level diff
- [ ] Proposed customer response and escalation export previewed before approval
- [ ] Explicit approval controls for correction, paid run, and customer text record actor and result
- [ ] Replay badge shown from API flag; synthetic incidents labeled; replay never presented as live
