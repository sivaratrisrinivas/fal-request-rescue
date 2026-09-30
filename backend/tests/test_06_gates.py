"""Harness watches the list surface and the gate paths, not just dispositions."""
import json

from eval.run_eval import probe_gates, safety_blob, score_suite


def test_safety_blob_includes_list_rows(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app(db_path=str(tmp_path / "t06g.db")))
    cid = client.post("/cases", json={
        "endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1",
        "report": "headline check", "payload": {"prompt": "x"}}).json()["id"]
    disp = client.post(f"/cases/{cid}/disposition", json={}).json()
    export = client.get(f"/cases/{cid}/export").json()
    blob = safety_blob(client, cid, disp, export)
    rows = json.loads(blob)["list"]
    assert any(r["id"] == cid and "headline check" in r["report"] for r in rows)


def test_gate_probes_all_green(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app(db_path=str(tmp_path / "t06h.db")))
    probes = probe_gates(client)
    assert probes == {"spend_blocked": True, "status_first": True, "unavailable": True}


def test_release_bar_watches_gates():
    report = score_suite(split="starter")
    assert report["gate_probes"] == {"spend_blocked": True, "status_first": True, "unavailable": True}
    assert report["release_bar"]["gates_green"] is True
