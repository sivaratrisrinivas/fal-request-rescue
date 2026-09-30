"""FastAPI surface: cases, evidence, investigate, disposition, approvals."""
import json
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import fal_live, llm, store
from .engine import build_disposition, customer_draft
from .investigate import ALLOWLIST, SCHEMA_DIR, run_investigation
from .redact import contains_secret, redact_json, redact_text

SESSION_CAP_USD = float(os.environ.get("SESSION_CAP_USD", "2.0"))
DAY_CAP_USD = float(os.environ.get("DAY_CAP_USD", "5.0"))

_PRICING: dict | None = None


def _price_for(endpoint_id: str) -> float:
    global _PRICING
    if _PRICING is None:
        _PRICING = {}
        try:
            doc = json.loads((SCHEMA_DIR / "pricing.json").read_text())
            for e in doc.get("endpoints", []):
                _PRICING[e["endpoint_id"]] = float(e.get("price_usd_per_run", 0.01))
        except (OSError, ValueError, KeyError):
            pass
    return _PRICING.get(endpoint_id, 0.01)


class CaseCreate(BaseModel):
    endpoint_id: str
    schema_version: str = "v1"
    report: str = ""
    payload: dict = Field(default_factory=dict)
    response_body: dict | None = None
    queue_events: list = Field(default_factory=list)
    webhook: dict | None = None
    origin: str = "analyst"


class EvidenceAttach(BaseModel):
    kind: str
    source: str = "analyst"
    content: dict = Field(default_factory=dict)


class DispositionRequest(BaseModel):
    use_llm: bool = False


class ApproveRequest(BaseModel):
    action_type: str
    actor: str = "analyst"


class LiveTestRequest(BaseModel):
    cost_estimate_usd: float | None = None
    model_recommends: bool = False
    mode: str = "record"
    status_checked: bool = False


class StatusCheckRequest(BaseModel):
    request_id: str


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
            origin=body.origin,
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
            origin=str(body.get("origin", "analyst")),
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

    @app.post("/cases/{case_id}/disposition")
    def disposition(case_id: str, body: DispositionRequest):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        inv = run_investigation(case)
        out = build_disposition(case, inv)
        if body.use_llm:
            # Redacted summary only: verdicts and codes, never raw payload text.
            summary = {"endpoint_id": case["endpoint_id"], "schema_version": case["schema_version"],
                       "schema_error_codes": [e["code"] for e in inv["schema_errors"]],
                       "queue_verdicts": [q["verdict"] for q in inv["queue"]],
                       "webhook_verified": inv["webhook"]["verified"]}
            try:
                draft = llm.draft_disposition(summary)
            except llm.ToolRejected as exc:
                return _error(422, "TOOL_REJECTED", str(exc))
            except RuntimeError as exc:
                return _error(503, "LLM_UNAVAILABLE", str(exc))
            except ValueError as exc:
                return _error(422, "LLM_INVALID", str(exc))
            except Exception as exc:
                # Transport/rate-limit failures (e.g. free-tier 429): the
                # deterministic engine already decided; report, don't 500.
                return _error(503, "LLM_UNAVAILABLE", f"{type(exc).__name__}")
            if contains_secret(json.dumps(draft.get("missing", []))):
                return _error(422, "LLM_INVALID", "Draft contains secret-like text")
            # Enforce here, not only in the adapter: a substituted or
            # compromised adapter must not smuggle in an outside tool.
            if draft.get("tool") not in ALLOWLIST:
                return _error(422, "TOOL_REJECTED",
                              f"tool '{draft.get('tool')}' outside allowlist")
            if draft.get("disposition") not in ("correction", "need-information", "escalation"):
                return _error(422, "LLM_INVALID",
                              f"bad disposition '{draft.get('disposition')}'")
            if out["disposition"] == "need-information" and draft.get("missing"):
                out["missing"] = [str(m) for m in draft["missing"]]
        saved_findings = store.save_findings(db_path, case_id, inv["findings"])
        store.save_action(db_path, case_id, "disposition", store._digest(inv),
                          {"disposition": out["disposition"]})
        return {"case_id": case_id, **out, "findings": saved_findings,
                "diagnostics_used": inv["diagnostics_used"]}

    @app.get("/cases/{case_id}/history")
    def history(case_id: str):
        hist = store.history(db_path, case_id)
        if hist is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return hist

    @app.get("/cases/{case_id}/customer-draft")
    def draft(case_id: str):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        if store.latest_disposition(db_path, case_id) is None:
            return _error(404, "NOT_FOUND", f"No disposition for case {case_id} yet")
        inv = run_investigation(case)
        return {"case_id": case_id, "draft": customer_draft(case, build_disposition(case, inv))}

    @app.post("/cases/{case_id}/approve")
    def approve(case_id: str, body: ApproveRequest):
        if store.get_case(db_path, case_id) is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        return store.approve_action(db_path, case_id, body.action_type, body.actor)

    @app.post("/cases/{case_id}/replay", status_code=200)
    def replay(case_id: str):
        """Replay-first execution: no credentials, no network, fixture-cited."""
        from datetime import datetime, timezone

        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        submitted = datetime.now(timezone.utc).isoformat()
        inv = run_investigation(case)
        disp = build_disposition(case, inv)
        result = {"mode": "replay", "badge": "replay",
                  "fixture_source": case.get("origin", "analyst"),
                  "submitted_at": submitted,
                  "completed_at": datetime.now(timezone.utc).isoformat(),
                  "schema_errors": len(inv["schema_errors"]),
                  "disposition": disp["disposition"]}
        store.save_action(db_path, case_id, "replay", store._digest(inv), result,
                          approval_state="approved")
        return {"case_id": case_id, **result}

    @app.post("/cases/{case_id}/request-status")
    def request_status(case_id: str, body: StatusCheckRequest):
        """Status lookup that never fabricates: mock-labeled without a key."""
        if store.get_case(db_path, case_id) is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        if not fal_live.api_key():
            return {"request_id": body.request_id, "status": "UNKNOWN",
                    "source": "mock-status-api",
                    "note": "No live lookup performed without FAL_API_KEY."}
        return _error(404, "NO_STATUS_URL",
                      "No live submit on this case yet — submit first, then check its status_url")

    @app.post("/cases/{case_id}/live-test")
    def live_test(case_id: str, body: LiveTestRequest):
        case = store.get_case(db_path, case_id)
        if case is None:
            return _error(404, "NOT_FOUND", f"Case {case_id} not found")
        if body.mode == "live":
            inv = run_investigation(case)
            pending = [q["request_id"] for q in inv["queue"]
                       if q["status"] in ("IN_QUEUE", "IN_PROGRESS")]
            if pending and not body.status_checked:
                store.save_action(db_path, case_id, "live-test", store._digest({"pending": pending}),
                                  {"status": "rejected", "reason": "status unchecked"},
                                  approval_state="rejected")
                return _error(409, "CHECK_STATUS_FIRST",
                              f"Request(s) {', '.join(pending)} still pending — check status before a new run")
            if not fal_live.api_key():
                store.save_action(db_path, case_id, "live-test", store._digest({"mode": "live"}),
                                  {"status": "rejected", "reason": "no key"},
                                  approval_state="rejected")
                return _error(503, "LIVE_UNAVAILABLE", "Set FAL_API_KEY server-side for live runs")
            try:
                submitted = fal_live.submit(case["endpoint_id"], case["payload"])
                seen = fal_live.fetch_status(submitted["status_url"]) if submitted.get("status_url") else {"status": submitted["status"]}
            except Exception as exc:
                return _error(503, "LIVE_UNAVAILABLE", f"{type(exc).__name__}")
            cost = _price_for(case["endpoint_id"])
            spent = store.spend_total(db_path, case_id)
            if spent + cost > SESSION_CAP_USD or spent + cost > DAY_CAP_USD:
                store.save_action(db_path, case_id, "live-test", store._digest(submitted),
                                  {"status": "blocked"}, cost_estimate=cost, approval_state="blocked")
                return _error(403, "SPEND_BLOCKED", "Live cost exceeds caps")
            if not store.approved_action_exists(db_path, case_id, "live-test"):
                store.save_action(db_path, case_id, "live-test", store._digest(submitted),
                                  {"status": "rejected", "reason": "no approval"},
                                  cost_estimate=cost, approval_state="rejected")
                return _error(403, "APPROVAL_REQUIRED", "Analyst approval required before any paid run")
            action = store.save_action(
                db_path, case_id, "live-test", store._digest(submitted),
                {"status": submitted["status"], "request_id": submitted["request_id"],
                 "status_url": submitted.get("status_url"),
                 "submitted_at": submitted["submitted_at"],
                 "observed_status": seen["status"],
                 "cost_estimate_usd": cost},
                cost_estimate=cost, approval_state="approved")
            return action
        # Spend caps are code law: checked first, approvals never override them.
        cost = body.cost_estimate_usd if body.cost_estimate_usd is not None else _price_for(case["endpoint_id"])
        spent = store.spend_total(db_path, case_id)
        if spent + cost > SESSION_CAP_USD or spent + cost > DAY_CAP_USD:
            store.save_action(db_path, case_id, "live-test", store._digest({"cost": cost}),
                              {"status": "blocked", "model_recommends": body.model_recommends},
                              cost_estimate=cost, approval_state="blocked")
            return _error(403, "SPEND_BLOCKED",
                          f"Cost {cost} exceeds caps (session {SESSION_CAP_USD}, day {DAY_CAP_USD})")
        if not store.approved_action_exists(db_path, case_id, "live-test"):
            store.save_action(db_path, case_id, "live-test", store._digest({"cost": cost}),
                              {"status": "rejected", "reason": "no approval"},
                              cost_estimate=cost, approval_state="rejected")
            return _error(403, "APPROVAL_REQUIRED", "Analyst approval required before any paid run")
        action = store.save_action(db_path, case_id, "live-test", store._digest({"cost": cost}),
                                   {"status": "recorded"}, cost_estimate=cost,
                                   approval_state="approved")
        return action

    return app


app = create_app()
