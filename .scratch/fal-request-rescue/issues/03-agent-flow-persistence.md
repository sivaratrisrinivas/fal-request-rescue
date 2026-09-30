# 03: Constrained agent flow plus persistence and audit

**What to build:** Structured model flow that proposes exactly one disposition with confidence and uncertainty, persisted with a full audit trail, with spend and injection guards in code.

**Blocked by:** 02 deterministic-core.

**Status:** ready-for-agent

- [ ] Extraction records only present facts and explicit missing fields; every finding cites `source_evidence_ids`
- [ ] Every model response validated against schema; tool outside allowlist rejected
- [ ] Disposition is exactly one of correction (schema-valid diff), need-information (exact missing artifact, nothing invented), or escalation packet (issue, repro, sanitized payload, observed vs expected, evidence, falsifiable hypothesis)
- [ ] Persistence records case, evidence digests, findings, actions with approval state, and audit event per transition
- [ ] Prompt injection in ticket text cannot change tools or approvals; over-budget paid action blocked by code; contradictory/insufficient evidence abstains with missing list
- [ ] OpenRouter adapter is server-side only with redacted input; tests use mocked adapter
