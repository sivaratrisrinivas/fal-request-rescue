# fal Request Rescue (prototype, ticket 01)

Replay-first support investigation scaffold. Ticket 01 only: case CRUD/import/export,
redaction before save, 3 pinned schema snapshots, 10 synthetic fixtures.

## Run backend

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
