# 02: Deterministic investigation core via API

**What to build:** Code-proven validation and state interpretation behind HTTP endpoints with no model call, so the six initial case types resolve to evidence-linked findings.

**Blocked by:** 01 scaffold-evidence-cases.

**Status:** ready-for-agent

## Comments

Implemented 2026-09-30 (ticket 02). New: `investigate` core module, evidence attach
and investigate routes, queue/webhook persisted as evidence rows, shared redaction
helper (closes 01 review note). Full suite 20/20, 10-fixture sweep clean, no secret
in investigate output. Review: no repo standards docs; judgements only — growing
`create_case` param list hints at an evidence-bundle type (defer to 03), mock lookup
return currently uncited in findings (wire into finding sources in 03).

- [ ] Payload validated against pinned snapshot: missing field, bad enum with allowed values shown, out-of-range explained, unknown endpoint asks for clarification, stale snapshot flagged
- [ ] Queue-item states parsed per semantics: `IN_QUEUE` never reported as inference failure, `IN_PROGRESS` never as completion, `COMPLETED` with error inspects error fields first
- [ ] Webhook delivery kept separate from queue vocabulary; missing/invalid/stale signature rejected with reason; duplicates collapse to one logical action
- [ ] Secret in payload removed from storage, model context, and exports
- [ ] Fixed diagnostic allowlist enforced; mock lookup adapter returns cited evidence; no shell/browser/code execution path
