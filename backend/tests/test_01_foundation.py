"""Ticket 01 foundation: redact + case CRUD/import/export via API seam."""
import json
import pathlib

from fastapi.testclient import TestClient

from app.main import create_app
from app.redact import redact_json, contains_secret

FIXTURES = pathlib.Path(__file__).resolve().parents[2] / "fixtures"


def make_client(tmp_path):
    app = create_app(db_path=str(tmp_path / "test.db"))
    return TestClient(app)


def test_redact_strips_keys_nested():
    payload = {
        "prompt": "a cat",
        "api_key": "fal-SECRET123",
        "nested": {"password": "hunter2", "ok": 1},
        "text": "Bearer sk-abc123xyz here",
    }
    redacted, had_secret = redact_json(payload)
    assert had_secret is True
    dumped = json.dumps(redacted)
    assert "SECRET123" not in dumped
    assert "hunter2" not in dumped
    assert "sk-abc123xyz" not in dumped
    assert "[REDACTED]" in dumped
    assert redacted["nested"]["ok"] == 1


def test_redact_clean_payload_no_false_positive():
    payload = {"prompt": "a cat riding a bike", "num_images": 1}
    redacted, had_secret = redact_json(payload)
    assert had_secret is False
    assert redacted == payload
    assert contains_secret(json.dumps(payload)) is False


def test_create_case_redacts_secret(tmp_path):
    client = make_client(tmp_path)
    r = client.post(
        "/cases",
        json={
            "endpoint_id": "fal-ai/flux/schnell",
            "schema_version": "v1",
            "report": "customer says 500, key fal-SECRET999 in log",
            "payload": {"prompt": "hi", "api_key": "fal-SECRET999"},
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    dumped = json.dumps(body)
    assert "SECRET999" not in dumped
    assert body["endpoint_id"] == "fal-ai/flux/schnell"
    assert body["schema_version"] == "v1"


def test_list_cases_paginated_shape(tmp_path):
    client = make_client(tmp_path)
    client.post(
        "/cases",
        json={"endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1", "report": "a"},
    )
    client.post(
        "/cases",
        json={"endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1", "report": "b"},
    )
    r = client.get("/cases?page=1&pageSize=20")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body and "pagination" in body
    assert body["pagination"]["totalItems"] >= 2


def test_import_ten_fixtures_clean(tmp_path):
    client = make_client(tmp_path)
    files = sorted(FIXTURES.glob("case-*.json"))
    assert len(files) == 10, f"expected 10 fixtures, got {len(files)}: {files}"
    for f in files:
        raw = json.loads(f.read_text())
        r = client.post("/cases/import", json=raw)
        assert r.status_code == 201, f"{f.name}: {r.text}"
        assert "SECRET" not in json.dumps(r.json()), f.name


def test_export_round_trip(tmp_path):
    client = make_client(tmp_path)
    r = client.post(
        "/cases",
        json={
            "endpoint_id": "fal-ai/flux/schnell",
            "schema_version": "v1",
            "report": "export me",
            "payload": {"prompt": "a dog"},
        },
    )
    case_id = r.json()["id"]
    e = client.get(f"/cases/{case_id}/export")
    assert e.status_code == 200, e.text
    exported = e.json()
    assert exported["id"] == case_id
    assert exported["schema_version"] == "v1"
    assert "evidence" in exported
    # re-import exported document
    r2 = client.post("/cases/import", json=exported)
    assert r2.status_code == 201, r2.text
    assert r2.json()["id"] != case_id
