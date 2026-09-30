# 02: Deterministic investigation core via API

**What to build:** Code-proven validation and state interpretation behind HTTP endpoints with no model call, so the six initial case types resolve to evidence-linked findings.

**Blocked by:** 01 scaffold-evidence-cases.

**Status:** ready-for-agent

- [ ] Payload validated against pinned snapshot: missing field, bad enum with allowed values shown, out-of-range explained, unknown endpoint asks for clarification, stale snapshot flagged
- [ ] Queue-item states parsed per semantics: `IN_QUEUE` never reported as inference failure, `IN_PROGRESS` never as completion, `COMPLETED` with error inspects error fields first
- [ ] Webhook delivery kept separate from queue vocabulary; missing/invalid/stale signature rejected with reason; duplicates collapse to one logical action
- [ ] Secret in payload removed from storage, model context, and exports
- [ ] Fixed diagnostic allowlist enforced; mock lookup adapter returns cited evidence; no shell/browser/code execution path
