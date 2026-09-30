"""Ticket 06: eval harness, gold revision, release bar."""
import json
import pathlib

from eval.run_eval import score_case, score_suite

CASES = pathlib.Path(__file__).resolve().parents[2] / "eval" / "cases"


def load(name):
    return json.loads((CASES / name).read_text())


def test_case_01_gold_revised_to_need_information():
    raw = json.loads(open("../fixtures/case-01-missing-field.json").read())
    assert raw["gold_disposition"] == "need-information"


def test_score_case_match_and_safety(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    client = TestClient(create_app(db_path=str(tmp_path / "t06.db")))
    doc = load("dev-04a-paraphrase.json")
    result = score_case(client, doc)
    assert result["disposition_match"] is True
    assert result["safety"]["no_secrets"] is True
    assert result["safety"]["evidence_cited"] is True


def test_score_case_detects_disagreement():
    from fastapi.testclient import TestClient
    import tempfile

    from app.main import create_app

    client = TestClient(create_app(db_path=tempfile.mkdtemp() + "/t06b.db"))
    doc = load("dev-04a-paraphrase.json")
    doc = {**doc, "gold_disposition": "correction"}
    result = score_case(client, doc)
    assert result["disposition_match"] is False


def test_manifest_split_hygiene():
    manifest = json.loads((CASES.parent / "manifest.json").read_text())
    assert manifest["totals"] == {"dev": 30, "validation": 10, "heldout": 20}
    assert manifest["ambiguous_count"] >= 12
    by_base: dict = {}
    for entry in manifest["cases"]:
        by_base.setdefault(entry["base"], set()).add(entry["split"])
    assert all(len(splits) == 1 for splits in by_base.values()), "paraphrase leaked across splits"


def test_starter_suite_green():
    report = score_suite(split="starter")
    assert report["release_bar"]["starter_green"] is True
    assert report["safety"]["failures"] == []
