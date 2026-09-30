"""Ticket 08: persisted disposition doc readable without re-POSTing."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "t08.db")))


def create(client, **kw):
    base = {
        "endpoint_id": "fal-ai/flux/schnell",
        "schema_version": "v1",
        "report": "t08",
        "payload": {"prompt": "a cat"},
    }
    base.update(kw)
    r = client.post("/cases", json=base)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_disposition_doc_readable_without_repost(client):
    cid = create(client, payload={"prompt": "x", "image_size": "banner_99"})
    assert client.get(f"/cases/{cid}/disposition").status_code == 404
    posted = client.post(f"/cases/{cid}/disposition", json={}).json()
    assert posted["disposition"] == "correction"
    got = client.get(f"/cases/{cid}/disposition").json()
    assert got["disposition"] == "correction"
    assert got["corrected_payload"]["image_size"] == posted["corrected_payload"]["image_size"]
    assert got["findings"]
    assert all(f["source_evidence_ids"] for f in got["findings"])


def test_disposition_doc_has_no_secrets(client):
    cid = create(client, payload={"prompt": "x", "api_key": "fal-testkey3131"})
    client.post(f"/cases/{cid}/disposition", json={})
    assert "testkey3131" not in json.dumps(client.get(f"/cases/{cid}/disposition").json())


def test_need_info_doc_keeps_missing_list(client):
    cid = create(client, payload={"image_size": "square_hd"})
    client.post(f"/cases/{cid}/disposition", json={})
    got = client.get(f"/cases/{cid}/disposition").json()
    assert got["disposition"] == "need-information"
    assert any("prompt" in m for m in got["missing"])
