"""SQLite store for cases, evidence, audit events."""
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


def _connect(db_path: str) -> sqlite3.Connection:
    parent = os.path.dirname(os.path.abspath(db_path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    conn = _connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                endpoint_id TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                report_redacted TEXT NOT NULL,
                payload_redacted TEXT NOT NULL,
                response_redacted TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                had_secret INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id),
                kind TEXT NOT NULL,
                source TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                redacted_content TEXT NOT NULL,
                digest TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id),
                actor TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _audit(conn: sqlite3.Connection, case_id: str, actor: str, event_type: str, details: dict) -> None:
    conn.execute(
        "INSERT INTO audit_events (id, case_id, actor, event_type, timestamp, details)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (uuid.uuid4().hex[:12], case_id, actor, event_type, _now(), json.dumps(details)),
    )


def _add_evidence(
    conn: sqlite3.Connection, case_id: str, kind: str, source: str, content
) -> dict:
    eid = uuid.uuid4().hex[:12]
    captured = _now()
    body = json.dumps(content, default=str)
    digest = _digest(content)
    conn.execute(
        "INSERT INTO evidence (id, case_id, kind, source, captured_at, redacted_content, digest)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (eid, case_id, kind, source, captured, body, digest),
    )
    return {"id": eid, "kind": kind, "digest": digest}


def create_case(
    db_path: str,
    *,
    endpoint_id: str,
    schema_version: str,
    report_redacted: str,
    payload_redacted: dict,
    response_redacted=None,
    had_secret: bool = False,
    extra_evidence: list | None = None,
) -> dict:
    case_id = uuid.uuid4().hex[:12]
    created = _now()
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO cases (id, created_at, endpoint_id, schema_version,"
            " report_redacted, payload_redacted, response_redacted, status, had_secret)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?)",
            (
                case_id, created, endpoint_id, schema_version, report_redacted,
                json.dumps(payload_redacted), json.dumps(response_redacted) if response_redacted is not None else None,
                1 if had_secret else 0,
            ),
        )
        ev = []
        ev.append(_add_evidence(conn, case_id, "report", "analyst", {"report": report_redacted}))
        ev.append(_add_evidence(conn, case_id, "request_payload", "analyst", payload_redacted))
        if response_redacted is not None:
            ev.append(_add_evidence(conn, case_id, "response_body", "analyst", response_redacted))
        for item in extra_evidence or []:
            kind = str(item.get("kind", "attachment"))
            source = str(item.get("source", "import"))
            ev.append(_add_evidence(conn, case_id, kind, source, item.get("content", item)))
        _audit(conn, case_id, "analyst", "case.created", {"endpoint_id": endpoint_id})
        conn.commit()
    finally:
        conn.close()
    return {
        "id": case_id,
        "created_at": created,
        "endpoint_id": endpoint_id,
        "schema_version": schema_version,
        "report": report_redacted,
        "payload": payload_redacted,
        "status": "open",
        "had_secret": had_secret,
        "evidence": ev,
    }


def list_cases(db_path: str, page: int = 1, page_size: int = 20) -> dict:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    conn = _connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"]
        rows = conn.execute(
            "SELECT id, created_at, endpoint_id, schema_version, status"
            " FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, (page - 1) * page_size),
        ).fetchall()
    finally:
        conn.close()
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "data": [dict(r) for r in rows],
        "pagination": {"page": page, "pageSize": page_size, "totalItems": total, "totalPages": total_pages},
    }


def get_case(db_path: str, case_id: str) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            return None
        ev = conn.execute(
            "SELECT id, kind, source, captured_at, redacted_content, digest"
            " FROM evidence WHERE case_id = ? ORDER BY captured_at",
            (case_id,),
        ).fetchall()
    finally:
        conn.close()
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "endpoint_id": row["endpoint_id"],
        "schema_version": row["schema_version"],
        "report": row["report_redacted"],
        "payload": json.loads(row["payload_redacted"]),
        "response_body": json.loads(row["response_redacted"]) if row["response_redacted"] else None,
        "status": row["status"],
        "had_secret": bool(row["had_secret"]),
        "evidence": [
            {
                "id": e["id"], "kind": e["kind"], "source": e["source"],
                "captured_at": e["captured_at"],
                "redacted_content": json.loads(e["redacted_content"]), "digest": e["digest"],
            }
            for e in ev
        ],
    }
