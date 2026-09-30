# Spec: fal Request Rescue MVP

Status: ready-for-agent

## Problem Statement

As a support analyst handling fal API failures, I waste time correlating a customer ticket with the actual queue-item state, the pinned endpoint schema, and webhook delivery evidence, while risking secret leakage and unsafe paid retries. Client timeouts look like inference failures, webhook ERROR looks like queue failure, and malformed payloads get retried blindly. I need one case view that shows only redacted facts, deterministic schema errors, state interpretation, and a single evidence-linked disposition I can approve.

## Solution

Request Rescue gives the analyst a case workspace: create or import a case with ticket text plus redacted request/response, queue-item events, and webhook delivery records against a pinned schema snapshot. Deterministic code redacts secrets, validates the payload, parses queue-item and webhook delivery state, and enforces read-only-by-default plus approval and spend-cap gates. A constrained OpenRouter-backed flow (server-side only, temp 0, strict JSON validation) proposes exactly one disposition — correction, need-information, or escalation packet — with confidence, uncertainty, and evidence links. Replay mode with synthetic fixtures is the default with a visible badge; live test is opt-in, capped, and audited. Every transition emits an audit event.

## User Stories

1. As an analyst, I want to create a case from a sanitized ticket plus endpoint ID, so that investigation starts from a single owned unit.
2. As an analyst, I want to import a synthetic example case, so that I can demo without credentials or customer data.
3. As an analyst, I want the case pinned to a schema snapshot version, so that later endpoint changes do not invalidate the diagnosis.
4. As an analyst, I want secrets redacted before save and before any model send, so that API keys never reach storage, model context, or exports.
5. As an analyst, I want to attach redacted request payload and response body as evidence with source and capture time, so that findings cite facts.
6. As an analyst, I want to attach queue-item events and webhook delivery payloads with timestamps, so that state confusion is resolvable.
7. As an analyst, I want deterministic schema validation against the pinned snapshot, so that missing fields, bad enums, and range violations are code-proven.
8. As an analyst, I want queue-item status (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED` + `error_type`) interpreted per fal semantics, so that I never report inference failure from a queued item.
9. As an analyst, I want webhook delivery status and signature verification kept separate from queue-item vocabulary, so that callback ERROR is not misread as queue failure.
10. As an analyst, I want duplicate webhook deliveries collapsed to one logical action, so that replays do not double-count.
11. As an analyst, I want diagnostic selection limited to a fixed allowlist with no shell/browser/code execution, so that the tool cannot go off-policy.
12. As an analyst, I want read-only checks by default and explicit approval plus spend cap before any live test, so that paid runs are deliberate.
13. As an analyst, I want the tool to check request status by ID before suggesting a retry after a client timeout, so that ambiguous timeouts do not create duplicate paid requests.
14. As an analyst, I want a case timeline with linked evidence, so that I can follow what was observed and when.
15. As an analyst, I want a diagnosis with confidence and explicit uncertainty, so that I know what is proven vs assumed.
16. As an analyst, I want a field-level payload diff for corrections that is schema-valid, so that the fix is applicable.
17. As an analyst, I want a need-information disposition naming the exact missing artifact, so that follow-up is precise and invents nothing.
18. As an analyst, I want an escalation packet (issue, repro steps, sanitized payload, observed vs expected, evidence, falsifiable hypothesis), so that engineering can act without re-investigation.
19. As an analyst, I want to approve a correction, a paid run, and any customer-facing draft separately with identity recorded, so that accountability is auditable.
20. As an analyst, I want replay results clearly badged with fixture source, so that I never mistake a replay for a live test.
21. As an analyst, I want to export a case as JSON for replay, so that an engineer can reproduce the reasoning.
22. As an analyst, I want to export a customer draft or escalation packet, so that communication leaves the tool.
23. As an analyst, I want prompt-injection in ticket text to have no effect on tools or approval rules, so that untrusted text stays data.
24. As an analyst, I want over-budget paid actions blocked by code even if the model recommends them, so that spend caps hold.
25. As an analyst, I want abstention with listed missing evidence when evidence is contradictory or insufficient, so that the tool says what it cannot prove.
26. As a demo viewer, I want a three-minute path (report → redaction + snapshot → evidence + diff → bounded test → export → timing/eval/ROI), plus one ambiguous case showing abstention, so that value and limits are visible.

## Implementation Decisions

- Records follow handoff contracts using glossary terms: `case`, `evidence` (redacted content + digest + source + captured time), `finding` (category, observed fact, `source_evidence_ids`, confidence), `action` (type, input digest, approval state, result, cost estimate), audit event (actor, type, timestamp, details). One disposition per case.
- Deterministic core owns redaction, JSON-Schema validation, trace normalization, queue-item and webhook delivery state parsing, evidence citation, and execution policy. LLM never performs arithmetic, validation, redaction, or policy checks.
- Stack per ADR-0001: Python/FastAPI backend and worker, React/TypeScript frontend built with Bun toolchain, SQLite for local case data and audit trail. `fal-client` only inside optional server-side live adapter.
- Initial pinned endpoints: `fal-ai/flux/schnell`, `fal-ai/flux/dev/image-to-image`, `fal-ai/veo3` (or current public equivalents at Day 1); each with saved request schema and pricing reference plus snapshot version cited in every finding.
- OpenRouter adapter per ADR-0001/0002: server-side only, key never in frontend, temp 0, strict response-schema validation with reject-and-retry on invalid tool outside allowlist, redacted synthetic content only, free-plan aware with deterministic fallback on limit hit.
- Policy gates per ADR-0002: replay default with badge; live test requires explicit analyst approval plus per-session and per-day caps; timeout with existing request ID forces status check before new run; retryable errors cite policy with attempt cap; non-retryable malformed input gets correction or escalation, no loop.
- API surface (behavioral, not file paths): case create/import/get/list, evidence attach, investigation run returning findings + schema errors + disposition proposal, approval actions for correction/paid-run/customer-text, replay execution, optional live-test submit, case JSON export, customer/escalation export. Audit event on each transition.
- UI: case inbox + case detail, readable timeline, evidence links, payload diff, proposed customer response, escalation export, explicit approval controls, replay badge, spend display.
- Initial six case types in scope: missing required field, invalid enum, out-of-range parameter, queue/result-state confusion, webhook delivery/signature issue, insufficient evidence. Auth, rate-limit guidance, timeouts, unknown endpoint added only after core path passes.
- Evaluation: start with 10 gold synthetic cases mapping to release bar, expand to 60 (30/10/20, >=12 ambiguous, paraphrases in one split) with gold disposition, allowed/prohibited actions, evidence links. 20 pass criteria from handoff §Evaluation apply unchanged.

## Testing Decisions

- Good tests assert external behavior through the single agreed seam: deterministic investigation core exercised via API endpoints with LLM adapter mocked. No assertions on implementation internals, no live network, no real keys.
- Coverage: redaction (key in payload removed from storage/context/export), schema validation (missing/enum/range/unknown-endpoint/stale-snapshot), state parsing (all `IN_QUEUE`/`IN_PROGRESS`/`COMPLETED`+error, timeout+ID, retryable vs non-retryable, webhook ERROR vs queue vocab, missing/invalid/stale signature, duplicate dedup, missing ID), policy gates (over-budget blocked, injection cannot change tools/approvals, abstention on insufficient evidence with missing list).
- Prior art: none (greenfield). New pattern is API-level tests with fixture cases + mocked OpenRouter JSON; frontend asserts replay badge flag from API, not browser automation.
- Release bar enforced by tests: all safety/spend cases pass; >=90% disposition on supported held-out; every correction links evidence; no secret in stored input or export. Ambiguous scoring reported as disagreement with gold revision before any rate claim.

## Out of Scope

Full authentication, ticketing integration (mock Linear/CSV export only after core evidence path), automatic refunds, production configuration changes, fine-tuning, multi-agent orchestration, arbitrary tool calls, automatic customer replies. Billing Evidence and PoC Runner tracks remain alternatives, not this build. No claim on fal ticket volume, handling time, revenue loss, or cash savings beyond editable ROI scenario.

## Further Notes

- Build order Day 1-7 per handoff; deploy replay-default locally via Docker; 3-min walkthrough + ROI formula with editable inputs (`eligible cases/mo × min saved/60 × loaded hourly`), illustrative $3k-$48k/mo labeled scenario only.
- Research base in `/home/srinivas/fal-hiring-research.md`; public docs (errors, queue, webhooks, models, changelog) and TSE posting support mechanics, not private volumes.
- Respects `CONTEXT.md` glossary and ADR-0001 (stack split) / ADR-0002 (replay-first live adapter). Contradicts neither.
