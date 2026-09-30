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
            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id),
                category TEXT NOT NULL,
                observed_fact TEXT NOT NULL,
                source_evidence_ids TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS actions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL REFERENCES cases(id),
                action_type TEXT NOT NULL,
                input_digest TEXT NOT NULL,
                approval_state TEXT NOT NULL DEFAULT 'pending',
                result TEXT NOT NULL,
                cost_estimate REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )
        conn.commit()
        try:
            conn.execute("ALTER TABLE cases ADD COLUMN origin TEXT DEFAULT 'analyst'")
            conn.commit()
        except Exception:
            pass
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
    queue_events: list | None = None,
    webhook: dict | None = None,
    origin: str = "analyst",
) -> dict:
    case_id = uuid.uuid4().hex[:12]
    created = _now()
    conn = _connect(db_path)
    try:
        conn.execute(
            "INSERT INTO cases (id, created_at, endpoint_id, schema_version,"
            " report_redacted, payload_redacted, response_redacted, status, had_secret, origin)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?)",
            (
                case_id, created, endpoint_id, schema_version, report_redacted,
                json.dumps(payload_redacted), json.dumps(response_redacted) if response_redacted is not None else None,
                1 if had_secret else 0, origin,
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
        for qe in queue_events or []:
            ev.append(_add_evidence(conn, case_id, "queue_event", "status-api", qe))
        if webhook is not None:
            ev.append(_add_evidence(conn, case_id, "webhook_delivery", "callback", webhook))
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


def add_evidence(db_path: str, case_id: str, kind: str, source: str, content) -> dict | None:
    conn = _connect(db_path)
    try:
        if conn.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone() is None:
            return None
        ev = _add_evidence(conn, case_id, kind, source, content)
        _audit(conn, case_id, "analyst", "evidence.attached", {"kind": kind})
        conn.commit()
        return ev
    finally:
        conn.close()


def save_findings(db_path: str, case_id: str, findings: list) -> list:
    conn = _connect(db_path)
    try:
        saved = []
        for f in findings:
            fid = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO findings (id, case_id, category, observed_fact,"
                " source_evidence_ids, confidence, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (fid, case_id, f["category"], f["observed_fact"],
                 json.dumps(f.get("source_evidence_ids", [])), f.get("confidence", "medium"), _now()),
            )
            saved.append({**f, "id": fid})
        _audit(conn, case_id, "tool", "findings.recorded", {"count": len(saved)})
        conn.commit()
        return saved
    finally:
        conn.close()


def save_action(db_path: str, case_id: str, action_type: str, input_digest: str,
                result: dict, cost_estimate: float = 0.0,
                approval_state: str = "pending") -> dict:
    conn = _connect(db_path)
    try:
        aid = uuid.uuid4().hex[:12]
        conn.execute(
            "INSERT INTO actions (id, case_id, action_type, input_digest,"
            " approval_state, result, cost_estimate, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (aid, case_id, action_type, input_digest, approval_state,
             json.dumps(result), cost_estimate, _now()),
        )
        _audit(conn, case_id, "tool", f"action.{approval_state}",
               {"action_type": action_type, "action_id": aid})
        conn.commit()
        return {"id": aid, "action_type": action_type, "input_digest": input_digest,
                "approval_state": approval_state, "result": result, "cost_estimate": cost_estimate}
    finally:
        conn.close()


def approve_action(db_path: str, case_id: str, action_type: str, actor: str) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT id FROM actions WHERE case_id = ? AND action_type = ?"
            " AND approval_state = 'pending' ORDER BY created_at DESC LIMIT 1",
            (case_id, action_type),
        ).fetchone()
        if row is None:
            # Record the approval itself so the trail shows who approved what.
            aid = uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO actions (id, case_id, action_type, input_digest,"
                " approval_state, result, cost_estimate, created_at)"
                " VALUES (?, ?, ?, ?, 'approved', ?, 0, ?)",
                (aid, case_id, action_type, "approval", json.dumps({"by": actor}), _now()),
            )
        else:
            aid = row["id"]
            conn.execute("UPDATE actions SET approval_state = 'approved' WHERE id = ?", (aid,))
        _audit(conn, case_id, actor, "action.approved",
               {"action_type": action_type, "action_id": aid})
        conn.commit()
        saved = conn.execute("SELECT * FROM actions WHERE id = ?", (aid,)).fetchone()
        return {"id": saved["id"], "action_type": saved["action_type"],
                "approval_state": saved["approval_state"],
                "result": json.loads(saved["result"]), "cost_estimate": saved["cost_estimate"]}
    finally:
        conn.close()


def approved_action_exists(db_path: str, case_id: str, action_type: str) -> bool:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM actions WHERE case_id = ? AND action_type = ?"
            " AND approval_state = 'approved' LIMIT 1",
            (case_id, action_type),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def spend_total(db_path: str, case_id: str) -> float:
    """Sum of non-blocked live-test cost estimates: the per-session meter."""
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_estimate), 0) AS total FROM actions"
            " WHERE case_id = ? AND action_type = 'live-test' AND approval_state != 'blocked'",
            (case_id,),
        ).fetchone()
        return float(row["total"])
    finally:
        conn.close()


def history(db_path: str, case_id: str) -> dict | None:
    case = get_case(db_path, case_id)
    if case is None:
        return None
    conn = _connect(db_path)
    try:
        findings = [dict(r) for r in conn.execute(
            "SELECT id, category, observed_fact, source_evidence_ids, confidence"
            " FROM findings WHERE case_id = ? ORDER BY created_at", (case_id,)).fetchall()]
        for f in findings:
            f["source_evidence_ids"] = json.loads(f["source_evidence_ids"])
        actions = [dict(r) for r in conn.execute(
            "SELECT id, action_type, input_digest, approval_state, result, cost_estimate"
            " FROM actions WHERE case_id = ? ORDER BY created_at", (case_id,)).fetchall()]
        for a in actions:
            a["result"] = json.loads(a["result"])
        audit = [dict(r) for r in conn.execute(
            "SELECT actor, event_type, timestamp, details FROM audit_events"
            " WHERE case_id = ? ORDER BY timestamp", (case_id,)).fetchall()]
    finally:
        conn.close()
    return {"evidence": [{"id": e["id"], "kind": e["kind"], "digest": e["digest"]}
                         for e in case["evidence"]],
            "findings": findings, "actions": actions, "audit": audit}


def latest_disposition(db_path: str, case_id: str) -> str | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT result FROM actions WHERE case_id = ? AND action_type = 'disposition'"
            " ORDER BY created_at DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["result"]).get("disposition")
    finally:
        conn.close()


def latest_disposition_doc(db_path: str, case_id: str) -> dict | None:
    conn = _connect(db_path)
    try:
        row = conn.execute(
            "SELECT result FROM actions WHERE case_id = ? AND action_type = 'disposition'"
            " ORDER BY created_at DESC LIMIT 1",
            (case_id,),
        ).fetchone()
        if row is None:
            return None
        return json.loads(row["result"])
    finally:
        conn.close()


def list_cases(db_path: str, page: int = 1, page_size: int = 20) -> dict:
    page = max(1, page)
    page_size = min(100, max(1, page_size))
    conn = _connect(db_path)
    try:
        total = conn.execute("SELECT COUNT(*) AS n FROM cases").fetchone()["n"]
        rows = conn.execute(
            "SELECT id, created_at, endpoint_id, schema_version, status, origin"
            " FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (page_size, (page - 1) * page_size),
        ).fetchall()
    finally:
        conn.close()
    total_pages = max(1, (total + page_size - 1) // page_size)
    rows = [dict(r) for r in rows]
    for r in rows:
        r["disposition"] = latest_disposition(db_path, r["id"])
    return {
        "data": rows,
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
        "origin": row["origin"] if "origin" in row.keys() else "analyst",
        # Hard replay until ticket 05 adds the live path; the UI badges this flag.
        "replay": True,
        "disposition": latest_disposition(db_path, row["id"]),
        "evidence": [
            {
                "id": e["id"], "kind": e["kind"], "source": e["source"],
                "captured_at": e["captured_at"],
                "redacted_content": json.loads(e["redacted_content"]), "digest": e["digest"],
            }
            for e in ev
        ],
    }
