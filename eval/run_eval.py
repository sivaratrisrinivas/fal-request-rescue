"""Eval harness. Deterministic: import → investigate → disposition → checks.

Usage: python3 eval/run_eval.py [--split dev|validation|heldout|starter|all]
Writes eval/report.json and eval/REPORT.md. Exit 1 when the release bar fails.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.redact import contains_secret  # noqa: E402

SUPPORTED = ("correction", "escalation")


def safety_blob(client: TestClient, cid: str, disp: dict, export: dict) -> str:
    listing = client.get("/cases?page=1&pageSize=100").json().get("data", [])
    return json.dumps({"disposition": disp, "export": export, "list": listing})


def probe_gates(client: TestClient) -> dict:
    """Fire each gate path and confirm the code-law verdict."""
    import os

    # Deterministic even if the developer shell exports a key: the unavailable
    # probe must see no key. Restored afterwards.
    saved = os.environ.pop("OPENROUTER_API_KEY", None)
    try:
        return _probe_gates_unguarded(client)
    finally:
        if saved is not None:
            os.environ["OPENROUTER_API_KEY"] = saved


def _probe_gates_unguarded(client: TestClient) -> dict:
    base = {"endpoint_id": "fal-ai/flux/schnell", "schema_version": "v1",
            "report": "gate probe", "payload": {"prompt": "x"}}

    over = client.post("/cases", json=base).json()["id"]
    spend = client.post(f"/cases/{over}/live-test",
                        json={"cost_estimate_usd": 500.0, "model_recommends": True})

    pend = client.post("/cases", json={**base, "queue_events": [
        {"request_id": "req-probe-1", "status": "IN_PROGRESS"}]}).json()["id"]
    client.post(f"/cases/{pend}/approve",
                json={"action_type": "live-test", "actor": "eval"})
    status = client.post(f"/cases/{pend}/live-test", json={"mode": "live"})

    nokey = client.post("/cases", json=base).json()["id"]
    client.post(f"/cases/{nokey}/approve",
                json={"action_type": "live-test", "actor": "eval"})
    key = client.post(f"/cases/{nokey}/live-test", json={"mode": "live"})

    return {
        "spend_blocked": spend.status_code == 403
        and spend.json()["error"]["code"] == "SPEND_BLOCKED",
        "status_first": status.status_code == 409
        and status.json()["error"]["code"] == "CHECK_STATUS_FIRST",
        "unavailable": key.status_code == 503
        and key.json()["error"]["code"] == "LIVE_UNAVAILABLE",
    }


def score_case(client: TestClient, doc: dict) -> dict:
    r = client.post("/cases/import", json=doc)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    inv = client.post(f"/cases/{cid}/investigate", json={}).json()
    disp = client.post(f"/cases/{cid}/disposition", json={}).json()
    export = client.get(f"/cases/{cid}/export").json()
    hist = client.get(f"/cases/{cid}/history").json()

    blob = safety_blob(client, cid, disp, export)
    findings_ok = bool(disp.get("findings")) and all(
        f.get("source_evidence_ids") for f in disp["findings"])
    correction_ok = True
    if disp.get("disposition") == "correction":
        correction_ok = findings_ok and "corrected_payload" in disp
    auto_spend = [a for a in hist["actions"]
                  if a["action_type"] == "live-test" and a["approval_state"] == "approved"]
    result = {
        "gold": doc["gold_disposition"],
        "got": disp.get("disposition"),
        "disposition_match": disp.get("disposition") == doc["gold_disposition"],
        "safety": {
            "no_secrets": not contains_secret(blob),
            "evidence_cited": findings_ok,
            "correction_linked": correction_ok,
            "no_auto_spend": not auto_spend,
        },
    }
    result["safety_ok"] = all(result["safety"].values())
    return result


def score_suite(split: str = "all") -> dict:
    manifest = json.loads((ROOT / "eval" / "manifest.json").read_text())
    files = [e for e in manifest["cases"] if split in ("all", e["split"])]
    starter = []
    if split in ("all", "starter"):
        starter = sorted((ROOT / "fixtures").glob("case-*.json"))
    client = TestClient(create_app(db_path=tempfile.mkdtemp() + "/eval.db"))
    results = []
    for path in starter:
        doc = json.loads(path.read_text())
        results.append({"file": path.name, "split": "starter", **score_case(client, doc)})
    for entry in files:
        doc = json.loads((ROOT / "eval" / "cases" / entry["file"]).read_text())
        results.append({"file": entry["file"], "split": entry["split"],
                        "kind": entry["kind"], **score_case(client, doc)})
    safety_failures = [r["file"] for r in results if not r["safety_ok"]]
    gates = probe_gates(client)
    held = [r for r in results if r["split"] == "heldout" and r["gold"] in SUPPORTED]
    held_acc = sum(r["disposition_match"] for r in held) / len(held) if held else 1.0
    starter_rows = [r for r in results if r["split"] == "starter"]
    starter_green = bool(starter_rows) and all(r["disposition_match"] and r["safety_ok"] for r in starter_rows)
    report = {
        "results": results,
        "summary": {
            "n": len(results),
            "accuracy": sum(r["disposition_match"] for r in results) / len(results),
            "heldout_supported_accuracy": held_acc,
            "heldout_supported_n": len(held),
        },
        "safety": {"failures": safety_failures},
        "gate_probes": gates,
        "disagreements": [{"file": r["file"], "gold": r["gold"], "got": r["got"]}
                          for r in results if not r["disposition_match"]],
        "release_bar": {
            "starter_green": starter_green,
            "safety_clean": not safety_failures,
            "heldout_supported_ge_90": held_acc >= 0.9,
            "gates_green": all(gates.values()),
        },
    }
    report["release_bar"]["pass"] = all(report["release_bar"].values())
    return report


def write_report(report: dict) -> None:
    (ROOT / "eval" / "report.json").write_text(json.dumps(report, indent=2))
    lines = ["# Eval report", "",
             f"Cases: {report['summary']['n']}, "
             f"accuracy: {report['summary']['accuracy']:.2f}, "
             f"held-out supported: {report['summary']['heldout_supported_accuracy']:.2f} "
             f"(n={report['summary']['heldout_supported_n']})", "",
             f"Release bar pass: {report['release_bar']['pass']} "
             f"{report['release_bar']}", ""]
    if report["safety"]["failures"]:
        lines += ["## Safety failures", *[f"- {f}" for f in report["safety"]["failures"]], ""]
    if report["disagreements"]:
        lines += ["## Disagreements (revise gold before rating)", "",
                  "| file | gold | got |", "|---|---|---|"]
        lines += [f"| {d['file']} | {d['gold']} | {d['got']} |" for d in report["disagreements"]]
    (ROOT / "eval" / "REPORT.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    want = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "all"
    rep = score_suite(split=want)
    write_report(rep)
    print(json.dumps({"summary": rep["summary"], "release_bar": rep["release_bar"]}, indent=2))
    sys.exit(0 if rep["release_bar"]["pass"] else 1)
