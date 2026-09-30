# CONTEXT.md — fal Request Rescue (glossary only, no implementation)

Canonical domain language. If usage conflicts with this file, this file wins until explicitly revised.

## Terms

- **case**: An analyst-owned investigation unit in Request Rescue. One customer report + pinned endpoint schema + collected evidence + one disposition. Distinct from a third-party ticketing-system ticket.
- **ticket**: The external customer report as received (email/chat/Slack text). Raw input to a case, never trusted as fact until linked to evidence.
- **endpoint**: A fal model API identified by endpoint ID (e.g. `fal-ai/flux/schnell`). Always referenced with a pinned schema snapshot version.
- **schema snapshot**: The saved public request schema + pricing reference for an endpoint at a point in time. Diagnoses cite the snapshot version they used.
- **queue-item**: A single fal request tracked by request ID with queue status (`IN_QUEUE`, `IN_PROGRESS`, `COMPLETED`) plus separate `error_type` on failed completion. Distinct from the model inference outcome.
- **inference**: The model computation itself (succeeded / failed with error fields). Client timeout does not prove inference failed.
- **webhook delivery**: The callback attempt carrying a result, with its own status vocabulary (`OK`, `ERROR`, etc.) and signature. Distinct from queue-item status.
- **evidence**: A stored, redacted, digest-linked artifact attached to a case (payload, response, queue event, callback, log, timestamp). Has source and capture time.
- **finding**: An analyst- or tool-asserted interpretation of one or more evidence items (category, observed fact, confidence). Always cites `source_evidence_ids`.
- **correction**: A schema-valid field-level payload diff proposed against the pinned schema snapshot, plus a bounded test result. Never silently rewrites out-of-range input.
- **disposition**: Exactly one per case: `correction`, `need-information`, or `escalation`.
- **need-information**: A disposition requesting exact missing artifacts (request ID, timestamp, endpoint, trace detail). Invents no values.
- **escalation packet**: An engineering handoff: issue statement, repro steps, sanitized payload, observed vs expected, evidence links, falsifiable hypothesis.
- **replay**: Execution against a local synthetic fixture. Labeled in UI, never implied as live. Default mode, needs no credentials.
- **live test**: Opt-in server-side call to fal via adapter, with explicit approval and spend cap. Records request ID, timestamps, status, cost estimate.
- **redaction**: Removal of secrets (API keys, passwords, credentials) from storage, model context, and exports before save or send.
- **approval**: Explicit analyst consent for a paid run or customer-facing text. Records who approved and what the tool returned.
