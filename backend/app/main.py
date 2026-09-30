"""FastAPI surface for ticket 01: health, case CRUD/import/export."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import store
from .investigate import run_investigation
from .redact import redact_json, redact_text


class CaseCreate(BaseModel):
    endpoint_id: str
    schema_version: str = "v1"
    report: str = ""
    payload: dict = Field(default_factory=dict)
    response_body: dict | None = None
    queue_events: list = Field(default_factory=list)
    webhook: dict | None = None


class EvidenceAttach(BaseModel):
    kind: str
    source: str = "analyst"
    content: dict = Field(default_factory=dict)


def _redact_inputs(report: str, payload, response_body):
    """Single shared redaction path for create/import (see ticket 01 review)."""
    report_red, s1 = redact_text(str(report))
    payload_red, s2 = redact_json(payload if isinstance(payload, dict) else {"value": payload})
    resp_red, s3 = (None, False)
    if response_body is not None:
        resp_red, s3 = redact_json(response_body)
    return report_red, payload_red, resp_red, bool(s1 or s2 or s3)


def _error(status: int, code: str, message: str, details=None):
    body: dict = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status, content=body)


def create_app(db_path: str = "data/request_rescue.db") -> FastAPI:
    store.init_db(db_path)
    app = FastAPI(title="fal Request Rescue")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError):
        return _error(422, "VALIDATION_ERROR", "Invalid request data", exc.errors())

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/cases", status_code=201)
    def create_case(body: CaseCreate):
        report_red, payload_red, resp_red, had_secret = _redact_inputs(
            body.report, body.payload, body.response_body)
        queue_red, _ = redact_json(body.queue_events)
        webhook_red = None
        if body.webhook is not None:
            webhook_red, s = redact_json(body.webhook)
            had_secret = had_secret or s
        case = store.create_case(
            db_path,
            endpoint_id=body.endpoint_id,
            schema_version=body.schema_version,
            report_redacted=report_red,
            payload_redacted=payload_red,
            response_redacted=resp_red,
            had_secret=had_secret,
            queue_events=queue_red if isinstance(queue_red, list) else [],
            webhook=webhook_red,
        )
        return case

    @app.get("/cases")
    def list_cases(page: int = 1, pageSize: int = 20):
        return store.list_cases(db_path, page=page, page_size=pageSize)

    @app.get("/cases/{case_id}")
    def get_case(case_id: str):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return case

    @app.post("/cases/import", status_code=201)
    def import_case(body: dict):
        # Accept exported docs and raw fixture docs; always mint a new id.
        try:
            endpoint_id = body["endpoint_id"]
            schema_version = body.get("schema_version", "v1")
            report = body.get("report", "")
            payload = body.get("payload", {})
            response_body = body.get("response_body")
        except (KeyError, TypeError, AttributeError):
            return _error(422, "VALIDATION_ERROR", "Import requires endpoint_id")
        if not isinstance(endpoint_id, str) or not endpoint_id:
            return _error(422, "VALIDATION_ERROR", "Import requires endpoint_id")
        report_red, payload_red, resp_red, had_secret = _redact_inputs(
            report, payload, response_body)
        queue_raw = body.get("queue_events") if isinstance(body.get("queue_events"), list) else []
        queue_red, _ = redact_json(queue_raw)
        webhook_red = None
        if body.get("webhook") is not None:
            webhook_red, s = redact_json(body["webhook"])
            had_secret = had_secret or s
        extra = body.get("evidence") if isinstance(body.get("evidence"), list) else None
        case = store.create_case(
            db_path,
            endpoint_id=endpoint_id,
            schema_version=str(schema_version),
            report_redacted=report_red,
            payload_redacted=payload_red,
            response_redacted=resp_red,
            had_secret=had_secret,
            extra_evidence=extra,
            queue_events=queue_red if isinstance(queue_red, list) else [],
            webhook=webhook_red,
        )
        return case

    @app.get("/cases/{case_id}/export")
    def export_case(case_id: str):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return case

    @app.post("/cases/{case_id}/evidence", status_code=201)
    def attach_evidence(case_id: str, body: EvidenceAttach):
        content_red, _ = redact_json(body.content)
        ev = store.add_evidence(db_path, case_id, body.kind, body.source, content_red)
        if ev is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return ev

    @app.post("/cases/{case_id}/investigate")
    def investigate(case_id: str):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return run_investigation(case)

    return app


app = create_app()
