# Data notes

## Records

- `Case`: id, created_at, endpoint_id, schema_version, redacted report/payload,
  origin (`analyst` or `fixture:`/`eval:` source), status.
- `Evidence`: case_id, kind, source, captured_at, redacted content, sha256 digest.
- `Finding`: category, observed fact, `source_evidence_ids`, confidence.
- `Action`: type, input digest, approval state
  (pending/approved/blocked/rejected), result, cost estimate.
- `AuditEvent`: actor, event type, timestamp, details — one per transition.

## Snapshots and pricing

`schemas/` pins each endpoint's request JSON Schema plus `snapshot_version`
and `pricing.json` (prototype estimates only). Every finding cites the snapshot
version it validated against; stale pins are flagged, never silently used.

## Redaction and retention

Secrets (API keys, passwords, tokens, bearer credentials) are redacted before
storage, before any model send, and in exports. `had_secret` is recorded; raw
secrets never are. Local SQLite lives in a Docker volume (`api-data`) or
`backend/data/` (gitignored). No customer data ships in fixtures or eval cases.
