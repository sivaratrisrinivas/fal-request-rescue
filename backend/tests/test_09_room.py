"""Ticket 09: inbox rows carry report headlines for the waiting strip."""
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(db_path=str(tmp_path / "t09.db")))


def test_list_rows_include_redacted_report(client):
    r = client.post("/cases", json={
        "endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1",
        "report": "Lighthouse size wrong, key fal-testkey5150 in log",
        "payload": {"prompt": "x"},
    })
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    rows = client.get("/cases?page=1&pageSize=20").json()["data"]
    row = next(x for x in rows if x["id"] == cid)
    assert "Lighthouse size wrong" in row["report"]
    assert "testkey5150" not in json.dumps(row)
    assert "[REDACTED]" in row["report"]
