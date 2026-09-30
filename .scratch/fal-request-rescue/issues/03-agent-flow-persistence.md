# 03: Constrained agent flow plus persistence and audit

**What to build:** Structured model flow that proposes exactly one disposition with confidence and uncertainty, persisted with a full audit trail, with spend and injection guards in code.

**Blocked by:** 02 deterministic-core.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 03). New: `llm` server-side OpenRouter adapter
(temp 0, JSON mode, draft re-validated in route), `engine` deterministic
disposition (correction only when schema-valid and value-evidenced), findings
and actions tables with approval states, history endpoint, approve and capped
live-test intent endpoints (caps checked before approvals). Full suite 32/32.
Live-model check: free-tier list has 16 models; default set to an available
free ID, but drafting currently 429s — 503 fallback proven, deterministic path
unaffected. Sweep 9/10 vs fixture golds; case-01 disagrees correctly (gold says
correction, no prompt value evidenced — inventing one violates criterion 1;
gold revision belongs to 06). Review judgements: `_clamp_fix` bound parsing is
convoluted, simplify on next touch; broad transport `except` is deliberate.

- [ ] Extraction records only present facts and explicit missing fields; every finding cites `source_evidence_ids`
- [ ] Every model response validated against schema; tool outside allowlist rejected
- [ ] Disposition is exactly one of correction (schema-valid diff), need-information (exact missing artifact, nothing invented), or escalation packet (issue, repro, sanitized payload, observed vs expected, evidence, falsifiable hypothesis)
- [ ] Persistence records case, evidence digests, findings, actions with approval state, and audit event per transition
- [ ] Prompt injection in ticket text cannot change tools or approvals; over-budget paid action blocked by code; contradictory/insufficient evidence abstains with missing list
- [ ] OpenRouter adapter is server-side only with redacted input; tests use mocked adapter
