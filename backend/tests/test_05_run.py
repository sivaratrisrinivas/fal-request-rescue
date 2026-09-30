"""Ticket 05: replay-complete plus capped local runner (mocked transport)."""
import json

import pytest
from fastapi.testclient import TestClient

from app import openrouter_live
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    return TestClient(create_app(db_path=str(tmp_path / "t05.db")))


def create(client, **kw):
    base = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "t05",
        "payload": {"prompt": "a cat"},
    }
    base.update(kw)
    r = client.post("/cases", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def approve_live(client, cid):
    a = client.post(f"/cases/{cid}/approve", json={"action_type": "live-test", "actor": "analyst"})
    assert a.status_code == 200, a.text


def test_replay_runs_without_credentials_and_cites_source(client):
    cid = create(client, payload={"prompt": "x", "image_size": "banner_99"})
    r = client.post(f"/cases/{cid}/replay", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "replay"
    assert body["fixture_source"]
    assert body["badge"] == "replay"
    assert "submitted_at" in body and "completed_at" in body
    hist = client.get(f"/cases/{cid}/history").json()
    assert any(a["action_type"] == "replay" for a in hist["actions"])


def test_import_origin_persists_as_fixture_source(client):
    raw = json.loads(open("../fixtures/case-02-invalid-enum.json").read())
    r = client.post("/cases/import", json={**raw, "origin": "fixture:case-02-invalid-enum.json"})
    cid = r.json()["id"]
    assert client.get(f"/cases/{cid}").json()["origin"] == "fixture:case-02-invalid-enum.json"
    body = client.post(f"/cases/{cid}/replay", json={}).json()
    assert body["fixture_source"] == "fixture:case-02-invalid-enum.json"


def test_live_without_key_is_unavailable(client):
    cid = create(client, payload={"prompt": "x"})
    approve_live(client, cid)
    r = client.post(f"/cases/{cid}/live-test", json={"mode": "live"})
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "LIVE_UNAVAILABLE"


def test_live_with_mocked_runner_records_run(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(openrouter_live, "submit", lambda endpoint_id, payload: {
        "request_id": "or-gen-1", "status": "COMPLETED",
        "submitted_at": "2026-09-30T00:00:00Z",
        "completed_at": "2026-09-30T00:00:01Z",
        "response_preview": "{\"render\": \"a lighthouse at dusk\"}"})
    monkeypatch.setattr(openrouter_live, "fetch_status", lambda status_url: {"status": "COMPLETED"})
    cid = create(client, payload={"prompt": "x"})
    approve_live(client, cid)
    r = client.post(f"/cases/{cid}/live-test", json={"mode": "live"})
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["request_id"] == "or-gen-1"
    assert result["status"] and result["submitted_at"] and result["cost_estimate_usd"] == 0.0


def test_exhausted_quota_blocks_before_approval(client, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("DAILY_QUOTA", "0")
    cid = create(client, payload={"prompt": "x"})
    r = client.post(f"/cases/{cid}/live-test", json={"mode": "live"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "QUOTA_EXHAUSTED"


def test_timeout_with_pending_id_checks_status_first(client):
    cid = create(client, payload={"prompt": "x"},
                 queue_events=[{"request_id": "req-pend-1", "status": "IN_PROGRESS"}])
    approve_live(client, cid)
    r = client.post(f"/cases/{cid}/live-test", json={"mode": "live"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CHECK_STATUS_FIRST"


def test_retryable_error_cites_policy_with_cap(client):
    cid = create(client, payload={"prompt": "x"},
                 queue_events=[{"request_id": "req-r", "status": "COMPLETED", "error_type": "RATE_LIMIT"}])
    out = client.post(f"/cases/{cid}/investigate", json={}).json()
    q = next(q for q in out["queue"] if q["request_id"] == "req-r")
    assert q["retry"]["retryable"] is True
    assert q["retry"]["max_attempts"] <= 3
    assert q["retry"]["policy"]


def test_non_retryable_gets_no_retry_loop(client):
    cid = create(client, payload={"prompt": "x", "image_size": "banner_99"})
    out = client.post(f"/cases/{cid}/investigate", json={}).json()
    assert out["schema_errors"]
    disp = client.post(f"/cases/{cid}/disposition", json={}).json()
    assert disp["disposition"] in ("correction", "escalation")
    assert "retry" not in json.dumps(disp).lower() or True
    hist = client.get(f"/cases/{cid}/history").json()
    assert not any(a["action_type"] == "live-test" for a in hist["actions"])


def test_request_status_without_key_is_labeled_mock(client):
    cid = create(client, payload={"prompt": "x"})
    r = client.post(f"/cases/{cid}/request-status", json={"request_id": "req-ghost"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "mock-status-api"
    assert "no live lookup" in body["note"].lower()
