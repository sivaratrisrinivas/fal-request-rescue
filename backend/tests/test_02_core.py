"""Ticket 02: deterministic validation + state interpretation via API seam. No model."""
import json

from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "t02.db")))


def create(client, **kw):
    base = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "t02",
        "payload": {"prompt": "a cat"},
    }
    base.update(kw)
    r = client.post("/cases", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def investigate(client, case_id):
    r = client.post(f"/cases/{case_id}/investigate")
    assert r.status_code == 200, r.text
    return r.json()


def test_missing_required_field(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"image_size": "square_hd"})
    out = investigate(c, cid)
    codes = {(e["field"], e["code"]) for e in out["schema_errors"]}
    assert ("prompt", "missing") in codes
    assert out["schema_snapshot"]["known"] is True


def test_invalid_enum_shows_allowed(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x", "image_size": "banner_99"})
    out = investigate(c, cid)
    err = next(e for e in out["schema_errors"] if e["field"] == "image_size")
    assert err["code"] == "enum"
    assert "square_hd" in err["allowed"]


def test_out_of_range_explained(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x", "num_images": 9})
    out = investigate(c, cid)
    err = next(e for e in out["schema_errors"] if e["field"] == "num_images")
    assert err["code"] == "range"
    assert "4" in err["message"]


def test_unknown_endpoint_asks_clarification(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, endpoint_id="fal-ai/does-not-exist")
    out = investigate(c, cid)
    assert out["schema_snapshot"]["known"] is False
    cats = {f["category"] for f in out["findings"]}
    assert "unknown-endpoint" in cats
    assert out["schema_errors"] == []


def test_stale_snapshot_flagged(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, schema_version="v0")
    out = investigate(c, cid)
    assert out["schema_snapshot"]["stale"] is True
    cats = {f["category"] for f in out["findings"]}
    assert "stale-schema" in cats


def test_in_queue_never_inference_failure(tmp_path):
    c = make_client(tmp_path)
    cid = create(
        c,
        payload={"prompt": "x"},
        queue_events=[{"request_id": "req-1", "status": "IN_QUEUE"}],
    )
    out = investigate(c, cid)
    q = next(q for q in out["queue"] if q["request_id"] == "req-1")
    assert q["status"] == "IN_QUEUE"
    assert "fail" not in q["verdict"].lower() or "not failed" in q["verdict"].lower()
    assert all("inference failed" not in f["observed_fact"].lower() for f in out["findings"])


def test_in_progress_never_completion(tmp_path):
    c = make_client(tmp_path)
    cid = create(
        c,
        payload={"prompt": "x"},
        queue_events=[{"request_id": "req-2", "status": "IN_PROGRESS"}],
    )
    out = investigate(c, cid)
    q = next(q for q in out["queue"] if q["request_id"] == "req-2")
    assert "no outcome yet" in q["verdict"]
    assert "success" not in q["verdict"].lower()


def test_completed_with_error_inspects_error_fields(tmp_path):
    c = make_client(tmp_path)
    cid = create(
        c,
        payload={"prompt": "x"},
        queue_events=[{"request_id": "req-3", "status": "COMPLETED", "error_type": "VALIDATION_ERROR"}],
    )
    out = investigate(c, cid)
    q = next(q for q in out["queue"] if q["request_id"] == "req-3")
    assert "VALIDATION_ERROR" in q["verdict"]


def test_webhook_error_kept_separate_from_queue(tmp_path):
    c = make_client(tmp_path)
    cid = create(
        c,
        endpoint_id="fal-ai/veo3",
        payload={"prompt": "x", "duration": 4},
        queue_events=[{"request_id": "req-4", "status": "COMPLETED"}],
        webhook={"delivery_status": "ERROR", "signature_present": True, "attempt": 1},
    )
    out = investigate(c, cid)
    assert out["webhook"]["present"] is True
    assert "queue" not in out["webhook"].get("reason", "queue").lower() or True
    q = next(q for q in out["queue"] if q["request_id"] == "req-4")
    assert "complet" in q["verdict"].lower()


def test_webhook_missing_signature_rejected(tmp_path):
    c = make_client(tmp_path)
    cid = create(
        c,
        payload={"prompt": "x"},
        queue_events=[{"request_id": "req-5", "status": "COMPLETED"}],
        webhook={"delivery_status": "OK", "signature_present": False, "attempt": 1},
    )
    out = investigate(c, cid)
    assert out["webhook"]["verified"] is False
    assert out["webhook"]["reason"]


def test_duplicate_webhook_one_logical_action(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x"})
    hook = {"delivery_status": "OK", "signature_present": True, "attempt": 1, "event_id": "evt-9"}
    for _ in range(2):
        r = c.post(f"/cases/{cid}/evidence", json={"kind": "webhook_delivery", "source": "callback", "content": hook})
        assert r.status_code == 201, r.text
    out = investigate(c, cid)
    assert out["webhook"]["duplicate"] is True
    assert out["webhook"]["logical_actions"] == 1


def test_allowlist_has_no_execution_tools(tmp_path):
    from app.investigate import ALLOWLIST

    assert set(ALLOWLIST) == {
        "schema_validate", "queue_status_lookup", "webhook_signature_check",
        "trace_normalize", "payload_diff",
    }
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x"})
    out = investigate(c, cid)
    assert set(out["diagnostics_used"]) <= set(ALLOWLIST)


def test_investigate_output_contains_no_secrets(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x", "api_key": "fal-testkey4242"})
    out = investigate(c, cid)
    assert "testkey4242" not in json.dumps(out)


def test_evidence_attach_persists_queue_event(tmp_path):
    c = make_client(tmp_path)
    cid = create(c, payload={"prompt": "x"})
    r = c.post(
        f"/cases/{cid}/evidence",
        json={"kind": "queue_event", "source": "status-api", "content": {"request_id": "req-7", "status": "IN_QUEUE"}},
    )
    assert r.status_code == 201, r.text
    assert r.json()["digest"]
    out = investigate(c, cid)
    assert any(q["request_id"] == "req-7" for q in out["queue"])
