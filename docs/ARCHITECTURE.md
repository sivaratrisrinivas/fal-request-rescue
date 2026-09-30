# Architecture

Replay-first support investigation tool. Analyst flow: redacted case →
deterministic checks → one disposition (correction / need-information /
escalation packet), with human approval on paid runs and customer text.

## Components

- `backend/app` (Python/FastAPI): `redact` runs before save and before any
  model send; `investigate` owns schema validation, queue/webhook state parsing,
  evidence citation, and the fixed diagnostic allowlist (`ALLOWLIST`; no shell,
  browser, or code execution); `engine` decides the single disposition and
  renders deterministic customer drafts; `llm` is a server-side OpenRouter
  adapter (temp 0, JSON mode, draft re-validated in the route); `fal_live` is
  the server-side fal queue adapter (key in env only); `policy` classifies
  retryable errors with attempt caps; `store` is SQLite (cases, evidence,
  findings, actions, audit events).
- `frontend` (React/TS, Bun toolchain, nginx in deploy): inbox + case detail
  (timeline, evidence, diff, draft/packet preview, approvals, replay badge
  from the API `replay` flag).
- `schemas/`: pinned endpoint snapshots + pricing references cited by version.
- `fixtures/` + `eval/`: 10 gold starters, 60 generated cases (30/10/20),
  deterministic harness with release bar.

## Key decisions

- ADR-0001 (stack split), ADR-0002 (replay-first live adapter) in `docs/adr/`.
- Single test seam: deterministic core exercised through FastAPI with the LLM
  adapter mocked. No live network or keys in tests.
- Spend and approval guards are code law: caps checked before approvals, and
  approvals never override caps. Pending request IDs block new runs (409)
  until status is checked.
