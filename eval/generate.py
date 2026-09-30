"""Deterministic eval-case generator. No LLM: every variant is reviewable.

Families stay in one split (paraphrases never leak across splits).
Usage: python3 eval/generate.py  (writes eval/cases/*.json + eval/manifest.json)
"""
import copy
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
OUT = ROOT / "eval" / "cases"

REWORDS = [
    "Customer follow-up with the same symptom, worded differently: {r}",
    "Same failure seen on a second workspace, rephrased by the reporter: {r}",
    "Reworded ticket describing the identical issue: {r}",
]

VAGUE = "Customer says something looks wrong but gave no request ID, no timestamp, no payload."


def base(name):
    return json.loads((FIX / name).read_text())


def paraphrase(doc, i, origin):
    d = copy.deepcopy(doc)
    d["report"] = REWORDS[i % len(REWORDS)].format(r=doc["report"])
    d["origin"] = origin
    return d


def ambiguous_drop(doc, origin):
    d = copy.deepcopy(doc)
    d["report"] = VAGUE
    d["payload"] = {}
    d["response_body"] = None
    d.pop("queue_events", None)
    d.pop("webhook", None)
    d["gold_disposition"] = "need-information"
    d["allowed_actions"] = ["request_request_id"]
    d["prohibited_actions"] = ["fabricate_lookup", "propose_correction", "paid_retry"]
    d["evidence_refs"] = []
    d["origin"] = origin
    return d


def decisive_09(doc, j):
    variants = [
        {"queue_events": [{"request_id": "req-held-e1", "status": "COMPLETED", "error_type": "SERVER_ERROR"}],
         "report": "Run finished but the status shows SERVER_ERROR for req-held-e1."},
        {"queue_events": [{"request_id": "req-held-e2", "status": "COMPLETED", "error_type": "RATE_LIMIT"}],
         "report": "Rate limited on req-held-e2 after completion; customer asks about retry policy."},
        {"queue_events": [{"request_id": "req-held-e3", "status": "COMPLETED"}],
         "webhook": {"delivery_status": "ERROR", "signature_present": True, "attempt": 2},
         "report": "Callback delivery ERROR for completed req-held-e3."},
    ]
    d = copy.deepcopy(doc)
    v = variants[j % len(variants)]
    d.update(v)
    d["gold_disposition"] = "escalation"
    d["allowed_actions"] = ["escalate_with_packet"]
    d["prohibited_actions"] = ["blind_retry", "paid_rerun"]
    d["origin"] = ""
    return d


def decisive_10(doc, j):
    variants = [
        {"webhook": {"delivery_status": "ERROR", "signature_present": True, "attempt": 1},
         "report": "Verified callback reports ERROR for a completed request."},
        {"webhook": {"delivery_status": "OK", "signature_present": True, "signature_valid": False, "attempt": 1},
         "report": "Callback arrived with a signature that does not verify."},
        {"webhook": {"delivery_status": "OK", "signature_present": True, "signature_stale": True, "attempt": 1},
         "report": "Callback signature is stale for a completed request."},
    ]
    d = copy.deepcopy(doc)
    v = variants[j % len(variants)]
    d.update(v)
    d["gold_disposition"] = "escalation"
    d["origin"] = ""
    return d


def plan():
    """Yields (filename, split, base_key, kind, doc)."""
    bases = {
        "01": "case-01-missing-field.json",
        "02": "case-02-invalid-enum.json",
        "03": "case-03-out-of-range.json",
        "04": "case-04-queue-confusion.json",
        "05": "case-05-webhook-error.json",
        "06": "case-06-insufficient-evidence.json",
        "07": "case-07-stale-schema.json",
        "08": "case-08-unknown-endpoint.json",
        "09": "case-09-timeout-with-id.json",
        "10": "case-10-webhook-no-signature.json",
    }
    dev_n = {"01": 6, "02": 6, "03": 6, "04": 6, "05": 6}          # 30
    val_n = {"06": 3, "07": 3, "08": 4}                             # 10
    held_n = {"09": ("para", 5, "amb", 2, "decisive", 3),
              "10": ("para", 5, "amb", 2, "decisive", 3)}            # 20

    def emit(split, key, kind, i, doc):
        tag = f"{split}-{key}{chr(ord('a') + i)}"
        filename = f"{tag}-{kind}.json"
        doc["origin"] = f"eval:{filename}"
        return filename, split, key, kind, doc

    for key, n in {**dev_n, **val_n}.items():
        doc = base(bases[key])
        for i in range(n):
            if i % 3 == 2:
                d = ambiguous_drop(doc, "")
                yield emit("dev" if key in dev_n else "validation", key, "ambiguous", i, d)
            else:
                d = paraphrase(doc, i, "")
                yield emit("dev" if key in dev_n else "validation", key, "paraphrase", i, d)
    for key, (_, np, _, na, _, ne) in held_n.items():
        doc = base(bases[key])
        idx = 0
        for i in range(np):
            yield emit("heldout", key, "paraphrase", idx, paraphrase(doc, i, ""))
            idx += 1
        for _ in range(na):
            yield emit("heldout", key, "ambiguous", idx, ambiguous_drop(doc, ""))
            idx += 1
        for j in range(ne):
            maker = decisive_09 if key == "09" else decisive_10
            yield emit("heldout", key, "decisive", idx, maker(doc, j))
            idx += 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    manifest = {"cases": [], "totals": {}, "ambiguous_count": 0}
    for filename, split, base_key, kind, doc in plan():
        (OUT / filename).write_text(json.dumps(doc, indent=2) + "\n")
        manifest["cases"].append({"file": filename, "split": split, "base": base_key,
                                  "kind": kind, "gold": doc["gold_disposition"]})
        manifest["totals"][split] = manifest["totals"].get(split, 0) + 1
        if kind == "ambiguous":
            manifest["ambiguous_count"] += 1
    (OUT.parent / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(manifest["totals"], "ambiguous:", manifest["ambiguous_count"])


if __name__ == "__main__":
    main()
