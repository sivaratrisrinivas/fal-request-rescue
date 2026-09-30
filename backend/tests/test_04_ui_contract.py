"""Ticket 04: UI contract — disposition state, replay flag, customer draft."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "t04.db")))


def create(client, **kw):
    base = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "t04",
        "payload": {"prompt": "a cat"},
    }
    base.update(kw)
    r = client.post("/cases", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_list_rows_carry_disposition_state(client):
    cid = create(client, payload={"prompt": "x", "image_size": "banner_99"})
    rows = client.get("/cases?page=1&pageSize=20").json()["data"]
    row = next(r for r in rows if r["id"] == cid)
    assert row["endpoint_id"] == "fal-ai/flux/schnell"
    assert row["schema_version"] == "v1"
    assert row["disposition"] is None
    client.post(f"/cases/{cid}/disposition", json={})
    rows = client.get("/cases?page=1&pageSize=20").json()["data"]
    assert next(r for r in rows if r["id"] == cid)["disposition"] == "correction"


def test_detail_carries_replay_flag_and_disposition(client):
    cid = create(client, payload={"prompt": "x"})
    d = client.get(f"/cases/{cid}").json()
    assert d["replay"] is True
    assert d["disposition"] is None
    client.post(f"/cases/{cid}/disposition", json={})
    assert client.get(f"/cases/{cid}").json()["disposition"] == "need-information"


def test_customer_draft_matches_disposition(client):
    cid = create(client, payload={"prompt": "x", "image_size": "banner_99"})
    client.post(f"/cases/{cid}/disposition", json={})
    draft = client.get(f"/cases/{cid}/customer-draft")
    assert draft.status_code == 200, draft.text
    assert "image_size" in draft.json()["draft"]
    assert "approv" in draft.json()["draft"].lower()


def test_customer_draft_need_info_lists_missing(client):
    cid = create(client, payload={"image_size": "square_hd"})
    client.post(f"/cases/{cid}/disposition", json={})
    body = client.get(f"/cases/{cid}/customer-draft").json()
    assert "prompt" in body["draft"]


def test_customer_draft_before_disposition_404(client):
    cid = create(client, payload={"prompt": "x"})
    r = client.get(f"/cases/{cid}/customer-draft")
    assert r.status_code == 404


def test_customer_draft_contains_no_secrets(client):
    cid = create(client, payload={"prompt": "x", "api_key": "fal-testkey9090"})
    client.post(f"/cases/{cid}/disposition", json={})
    body = client.get(f"/cases/{cid}/customer-draft").json()
    assert "testkey9090" not in json.dumps(body)
