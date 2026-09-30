# Replay-first with server-side live adapter

Cases run against local synthetic fixtures by default with a visible replay badge and no credentials. Live fal calls are opt-in only, executed server-side via `fal-client`, requiring explicit analyst approval plus per-session and per-day spend caps, recording request ID, timestamps, status, and cost estimate. Never imply replay is live; never resubmit after ambiguous timeout without checking request status first.
