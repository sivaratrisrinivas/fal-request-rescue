# fal Request Rescue (prototype)

Replay-first support investigation scaffold. Ticket 01 only: case CRUD/import/export,
redaction before save, 3 pinned schema snapshots, 10 synthetic fixtures.

## Deploy (Docker, replay default, no credentials)

```bash
docker compose up -d --build
# UI: http://localhost:8080   API: http://localhost:8000
docker compose down
```

Live paths stay opt-in and capped; they need `FAL_API_KEY` / `OPENROUTER_API_KEY`
in the server environment (never in the repo or frontend).

## Run backend (local dev)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000
```

Health: `GET /health`. Cases: `POST /cases`, `GET /cases?page=1&pageSize=20`,
`GET /cases/{id}`, `POST /cases/import`, `GET /cases/{id}/export`.

## Run frontend (Bun)

```bash
cd frontend
bun install
bun run dev   # proxies /cases + /health to :8000
```

## Tests

```bash
cd backend
python -m pytest tests/ -q
```

## Notes

- Secrets are redacted before storage and never sent to any model (no model call in 01).
- `schemas/` holds pinned snapshots + pricing. `fixtures/case-*.json` are the 10 gold cases.
- Default SQLite file is `backend/data/request_rescue.db` (gitignored); tests use tmp files.
- Docs: `docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/DEMO.md` (3-min walkthrough),
  `docs/ROI.md` (editable scenario), `eval/REPORT.md` (70 cases, bar pass).
