# Demo script (3 minutes, replay mode, no credentials)

Setup: `docker compose up -d --build`, open http://localhost:8080.
Seed (optional): import `fixtures/case-02-invalid-enum.json` via the API —
it is the worked example below.

## Walkthrough

- 0:00–0:25. Open the synthetic customer report (`banner_99` enum case) and
  its broken payload. Note the replay badge: synthetic fixture, not live.
- 0:25–0:55. Run investigate. Show the pinned `v1` snapshot and the redacted
  fake credential (stored as `[REDACTED]`, flagged by `had_secret`).
- 0:55–1:35. Show the evidence trail, the deterministic schema failure with
  allowed values, and the field-level correction diff.
- 1:35–2:05. Run replay (badge + fixture source + timestamps) and approve
  the correction as `analyst`. The Gemini prompt preview stays capped and
  quota-guarded — and stays a preview: it never submits to fal.
- 2:05–2:30. Preview the customer draft, then export the case JSON.
- 2:30–3:00. Show `eval/REPORT.md` (70 cases, bar pass) and `docs/ROI.md`
  inputs — labeled scenario, fal's actual savings unknown.

## Abstention beat (extra 30s)

Open `fixtures/case-06-insufficient-evidence.json`: no request ID, no payload.
Run disposition → need-information naming the exact missing artifacts. The tool
says what it cannot prove.

Teardown: `docker compose down`.
