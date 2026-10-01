"""Deterministic investigation core. No model calls, no execution tools."""
import json
import pathlib

import jsonschema

from .policy import classify

ALLOWLIST = (
    "schema_validate",
    "queue_status_lookup",
    "webhook_signature_check",
    "trace_normalize",
    "payload_diff",
)

SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[2] / "schemas"
if not SCHEMA_DIR.is_dir():
    # Container layout (/srv/app + /srv/schemas): schemas sit beside the package.
    SCHEMA_DIR = pathlib.Path(__file__).resolve().parents[1] / "schemas"

_snapshots: dict | None = None


def _load_snapshots() -> dict:
    global _snapshots
    if _snapshots is None:
        _snapshots = {}
        for path in SCHEMA_DIR.glob("*.v*.json"):
            if path.name == "pricing.json":
                continue
            try:
                doc = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            _snapshots[(doc.get("endpoint_id"), doc.get("snapshot_version"))] = doc
    return _snapshots


def _known_versions(endpoint_id: str) -> list:
    return sorted(v for (e, v) in _load_snapshots() if e == endpoint_id)


def snapshot_status(endpoint_id: str, version: str) -> dict:
    versions = _known_versions(endpoint_id)
    known = version in versions
    return {
        "endpoint_id": endpoint_id,
        "version": version,
        "known": known,
        "stale": bool(versions) and not known,
        "latest_pinned": versions[-1] if versions else None,
    }


def validate_payload(payload: dict, endpoint_id: str, version: str) -> list:
    snaps = _load_snapshots()
    schema = snaps.get((endpoint_id, version))
    if schema is None:
        return []
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path)):
        if err.validator == "required":
            missing = err.message.split("'")[1] if "'" in err.message else err.message
            errors.append({
                "field": missing, "code": "missing",
                "message": f"Missing required field '{missing}'.",
            })
        elif err.validator == "enum":
            field = ".".join(str(p) for p in err.absolute_path)
            errors.append({
                "field": field, "code": "enum",
                "message": f"Invalid value for '{field}'. Allowed: {err.validator_value}.",
                "allowed": list(err.validator_value),
            })
        elif err.validator in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                               "minLength", "maxLength", "minItems", "maxItems", "multipleOf"):
            field = ".".join(str(p) for p in err.absolute_path)
            errors.append({
                "field": field, "code": "range",
                "message": f"Out-of-range value for '{field}': {err.message} (constraint: {err.validator_value}).",
                "constraint": err.validator,
                "bound": err.validator_value,
            })
        else:
            field = ".".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append({"field": field, "code": err.validator, "message": err.message})
    return errors


def interpret_queue(events: list) -> list:
    out = []
    for ev in events:
        rid = ev.get("request_id", "unknown")
        status = str(ev.get("status", "UNKNOWN"))
        if status == "IN_QUEUE":
            verdict = "Queued — inference has not run; not failed. Wait for completion evidence."
        elif status == "IN_PROGRESS":
            verdict = "Running — not complete; no outcome yet."
        elif status == "COMPLETED":
            err = ev.get("error_type")
            if err:
                verdict = f"Completed with error {err} — inspect error fields before disposition."
            else:
                verdict = "Completed successfully."
        else:
            verdict = f"Unknown status '{status}' — request clarification, assume nothing."
        item = {"request_id": rid, "status": status, "verdict": verdict}
        if status == "COMPLETED" and ev.get("error_type"):
            item["retry"] = classify(ev.get("error_type"))
        out.append(item)
    return out


def _delivery_key(d: dict, index: int) -> str:
    return str(d.get("event_id") or d.get("delivery_id") or f"attempt-{d.get('attempt', index)}")


def interpret_webhook(deliveries: list) -> dict:
    if not deliveries:
        return {"present": False, "verified": False, "verification": "absent",
                "reason": "No webhook delivery evidence attached.",
                "duplicate": False, "logical_actions": 0, "status": None}
    keys = [_delivery_key(d, i) for i, d in enumerate(deliveries)]
    seen: dict = {}
    for k in keys:
        seen[k] = seen.get(k, 0) + 1
    duplicate = any(n > 1 for n in seen.values())
    first = deliveries[0]
    status = first.get("delivery_status")
    # Missing or null validation fields never count as a successful check.
    # "Reported valid" is imported evidence, not cryptographic proof — this
    # app performs no signature verification of its own.
    if first.get("signature_present") is not True:
        verification = "unverified"
        verified, reason = False, "Missing webhook signature — reject callback as unverified."
    elif first.get("signature_valid") is False:
        verification = "invalid"
        verified, reason = False, "Webhook signature reported invalid — reject callback as unverified."
    elif first.get("signature_stale") is True:
        verification = "stale"
        verified, reason = False, "Webhook signature reported stale — reject callback as unverified."
    elif first.get("signature_valid") is True:
        verification = "reported-valid"
        verified, reason = True, ("Webhook signature reported valid in imported evidence "
                                  "(not independently verified) — treat as reported, not proven.")
    else:
        verification = "unknown"
        verified, reason = False, ("Signature present but validation status missing — "
                                   "reject callback as unverified.")
    if status == "ERROR":
        reason += (" Callback delivery ERROR is a delivery result, not a queue-state"
                   " failure; the queue-item status decides the inference outcome.")
    return {"present": True, "verified": verified, "verification": verification,
            "reason": reason,
            "duplicate": duplicate, "logical_actions": len(seen), "status": status}


def run_investigation(case: dict) -> dict:
    endpoint_id = case["endpoint_id"]
    version = case["schema_version"]
    snap = snapshot_status(endpoint_id, version)
    schema_errors = validate_payload(case.get("payload") or {}, endpoint_id, version)

    by_kind: dict = {}
    for ev in case.get("evidence", []):
        by_kind.setdefault(ev["kind"], []).append(ev)
    queue_events = [e["redacted_content"] for e in by_kind.get("queue_event", [])]
    deliveries = [e["redacted_content"] for e in by_kind.get("webhook_delivery", [])]

    queue = interpret_queue(queue_events)
    webhook = interpret_webhook(deliveries)

    findings = []
    ev_ids = {kind: [e["id"] for e in evs] for kind, evs in by_kind.items()}
    payload_ids = ev_ids.get("request_payload", [])

    if not snap["known"] and _known_versions(endpoint_id) == []:
        findings.append({"category": "unknown-endpoint",
                         "observed_fact": f"Unknown endpoint '{endpoint_id}' — ask for clarification; no endpoint invented.",
                         "source_evidence_ids": ev_ids.get("report", []), "confidence": "high"})
    if snap["stale"]:
        findings.append({"category": "stale-schema",
                         "observed_fact": f"Case pins {version} but latest snapshot is {snap['latest_pinned']} — flag version mismatch before correction.",
                         "source_evidence_ids": payload_ids, "confidence": "high"})
    for err in schema_errors:
        findings.append({"category": "schema-validation",
                         "observed_fact": err["message"],
                         "source_evidence_ids": payload_ids, "confidence": "high"})
    if queue_events:
        for q, ev in zip(queue, by_kind.get("queue_event", [])):
            findings.append({"category": "queue-state",
                             "observed_fact": f"{q['request_id']}: {q['verdict']}",
                             "source_evidence_ids": [ev["id"]], "confidence": "high"})
    if webhook["present"] and not webhook["verified"]:
        findings.append({"category": "webhook-unverified",
                         "observed_fact": webhook["reason"],
                         "source_evidence_ids": ev_ids.get("webhook_delivery", []), "confidence": "high"})

    diagnostics = ["schema_validate", "trace_normalize"]
    if queue_events:
        diagnostics.append("queue_status_lookup")
    if webhook["present"]:
        diagnostics.append("webhook_signature_check")
    if schema_errors:
        diagnostics.append("payload_diff")
    assert set(diagnostics) <= set(ALLOWLIST)

    return {"case_id": case["id"], "schema_snapshot": snap, "schema_errors": schema_errors,
            "queue": queue, "webhook": webhook, "findings": findings,
            "diagnostics_used": diagnostics}
