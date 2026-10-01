"""Safeguard regressions: import redaction, webhook states, preview labels, status gate."""
import json

import pytest
from fastapi.testclient import TestClient

from app import gemini_live
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return TestClient(create_app(db_path=str(tmp_path / "t10.db")))


def create(client, **kw):
    base = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "t10",
        "payload": {"prompt": "a cat"},
    }
    base.update(kw)
    r = client.post("/cases", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def investigate(client, cid):
    r = client.post(f"/cases/{cid}/investigate", json={})
    assert r.status_code == 200, r.text
    return r.json()


# --- 1. Imported extra evidence is redacted before storage ---

def test_import_redacts_extra_evidence_top_level_and_nested(client):
    raw = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "import with secrets",
        "payload": {"prompt": "x"},
        "evidence": [
            {"kind": "log", "source": "import",
             "content": {"token": "fal-EVTOK123",
                         "nested": {"api_key": "fal-EVNEST456"},
                         "safe": "stays-visible"}},
        ],
    }
    r = client.post("/cases/import", json=raw)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["had_secret"] is True
    for doc in (client.get(f"/cases/{cid}").json(),
                client.get(f"/cases/{cid}/export").json(),
                client.get(f"/cases/{cid}/history").json()):
        assert "EVTOK123" not in json.dumps(doc)
        assert "EVNEST456" not in json.dumps(doc)
    export = client.get(f"/cases/{cid}/export").json()
    log = next(e for e in export["evidence"] if e["kind"] == "log")
    assert log["source"] == "import"
    assert log["redacted_content"]["safe"] == "stays-visible"
    assert "[REDACTED]" in json.dumps(log)


def test_import_without_secrets_leaves_flag_down(client):
    raw = {"endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1",
           "report": "clean", "payload": {"prompt": "x"},
           "evidence": [{"kind": "note", "source": "import", "content": {"text": "hello"}}]}
    r = client.post("/cases/import", json=raw)
    assert r.status_code == 201, r.text
    assert r.json()["had_secret"] is False


# --- 2. Webhook verification states ---

def webhook_state(client, hook):
    cid = create(client, payload={"prompt": "x"}, webhook=hook)
    return investigate(client, cid)["webhook"]


def test_webhook_missing_fields_is_not_verified(client):
    w = webhook_state(client, {"delivery_status": "OK", "signature_present": True, "attempt": 1})
    assert w["verified"] is False and w["verification"] == "unknown"


def test_webhook_null_fields_are_not_verified(client):
    w = webhook_state(client, {"delivery_status": "OK", "signature_present": True,
                               "signature_valid": None, "signature_stale": None, "attempt": 1})
    assert w["verified"] is False and w["verification"] == "unknown"


def test_webhook_reported_invalid(client):
    w = webhook_state(client, {"delivery_status": "OK", "signature_present": True,
                               "signature_valid": False, "attempt": 1})
    assert w["verified"] is False and w["verification"] == "invalid"


def test_webhook_reported_stale(client):
    w = webhook_state(client, {"delivery_status": "OK", "signature_present": True,
                               "signature_valid": True, "signature_stale": True, "attempt": 1})
    assert w["verified"] is False and w["verification"] == "stale"


def test_webhook_reported_valid_is_labeled_reported_not_proven(client):
    w = webhook_state(client, {"delivery_status": "OK", "signature_present": True,
                               "signature_valid": True, "attempt": 1})
    assert w["verified"] is True and w["verification"] == "reported-valid"
    assert "not independently verified" in w["reason"]


# --- 3. Gemini path labeled as preview ---

def test_preview_result_names_provider_and_disclaims_fal(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_live, "submit", lambda endpoint_id, payload: {
        "request_id": "gem-1", "status": "COMPLETED",
        "submitted_at": "2026-09-30T00:00:00Z",
        "completed_at": "2026-09-30T00:00:01Z",
        "response_preview": "{}"})
    monkeypatch.setattr(gemini_live, "fetch_status", lambda status_url: {"status": "COMPLETED"})
    cid = create(client, payload={"prompt": "x"})
    client.post(f"/cases/{cid}/approve", json={"action_type": "live-test", "actor": "analyst"})
    result = client.post(f"/cases/{cid}/live-test", json={"mode": "live"}).json()["result"]
    assert result["provider"] == "gemini"
    assert result["kind"] == "prompt-preview"
    assert "not submitted to fal" in result["preview_note"]


# --- 4. Status gate is server-owned ---

def test_client_status_flag_cannot_bypass_pending_gate(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    cid = create(client, payload={"prompt": "x"},
                 queue_events=[{"request_id": "req-gate-1", "status": "IN_PROGRESS"}])
    client.post(f"/cases/{cid}/approve", json={"action_type": "live-test", "actor": "analyst"})
    r = client.post(f"/cases/{cid}/live-test",
                    json={"mode": "live", "status_checked": True})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CHECK_STATUS_FIRST"


def test_server_recorded_check_unlocks_pending_gate(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(gemini_live, "submit", lambda endpoint_id, payload: {
        "request_id": "gem-2", "status": "COMPLETED",
        "submitted_at": "2026-09-30T00:00:00Z",
        "completed_at": "2026-09-30T00:00:01Z",
        "response_preview": "{}"})
    monkeypatch.setattr(gemini_live, "fetch_status", lambda status_url: {"status": "COMPLETED"})
    cid = create(client, payload={"prompt": "x"},
                 queue_events=[{"request_id": "req-gate-2", "status": "IN_PROGRESS"}])
    client.post(f"/cases/{cid}/approve", json={"action_type": "live-test", "actor": "analyst"})
    chk = client.post(f"/cases/{cid}/request-status", json={"request_id": "req-gate-2"})
    assert chk.status_code == 200, chk.text
    r = client.post(f"/cases/{cid}/live-test", json={"mode": "live"})
    assert r.status_code == 200, r.text
    hist = client.get(f"/cases/{cid}/history").json()
    assert any(a["action_type"] == "status-check" for a in hist["actions"])
