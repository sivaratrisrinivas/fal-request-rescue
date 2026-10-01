"""Deterministic disposition engine. The model may draft; this module decides."""
import copy

from .investigate import validate_payload

AUTO_FIXABLE = {"enum", "range"}


def _clamp_fix(payload: dict, errors: list) -> dict:
    fixed = copy.deepcopy(payload)
    for err in errors:
        field = err["field"]
        if err["code"] == "enum":
            fixed[field] = err["allowed"][0]
        elif err["code"] == "range":
            current = fixed.get(field)
            bound = err.get("bound")
            if isinstance(current, (int, float)) and isinstance(bound, (int, float)):
                if err.get("constraint") in ("minimum", "exclusiveMinimum"):
                    fixed[field] = max(current, bound)
                else:
                    fixed[field] = min(current, bound)
                if isinstance(current, int):
                    fixed[field] = int(fixed[field])
    return fixed


def customer_draft(case: dict, disp: dict) -> str:
    """Deterministic customer-facing draft. Preview only — sending needs approval."""
    kind = disp["disposition"]
    if kind == "correction":
        fields = ", ".join(sorted((disp.get("corrected_payload") or {}).keys()))
        return ("Suggested fix, pending your approval — do not send yet:\n"
                f"The request failed schema validation. Proposed correction touches: {fields}.\n"
                "Approve the correction first, then reply with the corrected request.")
    if kind == "need-information":
        items = "\n".join(f"- {m}" for m in disp.get("missing", []))
        return ("To proceed we need the following evidence:\n"
                f"{items}\n"
                "Nothing has been rerun. Reply once the items above are provided.")
    issue = (disp.get("packet") or {}).get("issue", "Under triage.")
    return ("This needs engineering triage — do not promise a fix yet:\n"
            f"{issue}\n"
            f"Internal reference: {case['id']}. Escalation packet attached.")
def _packet(case: dict, inv: dict, issue: str, hypothesis: str) -> dict:
    ev = [{"id": e["id"], "kind": e["kind"], "digest": e["digest"]}
          for e in case.get("evidence", [])]
    return {
        "issue": issue,
        "repro_steps": [
            f"Import case export for {case['id']}.",
            f"Run investigate against {case['endpoint_id']}@{case['schema_version']}.",
            "Compare the cited evidence with the observed behavior below.",
        ],
        "sanitized_payload": case.get("payload") or {},
        "observed": "; ".join(f["observed_fact"] for f in inv.get("findings", [])) or issue,
        "expected": "Documented fal behavior for the cited state and schema.",
        "evidence": ev,
        "hypothesis": hypothesis,
    }


def build_disposition(case: dict, inv: dict) -> dict:
    endpoint_id = case["endpoint_id"]
    version = case["schema_version"]
    snap = inv["schema_snapshot"]
    errors = inv["schema_errors"]
    queue = inv["queue"]
    webhook = inv["webhook"]
    report = (case.get("report") or "").lower()

    def need(missing, uncertainty):
        return {"disposition": "need-information", "confidence": "high",
                "uncertainty": uncertainty, "missing": missing}

    if not snap["known"] and snap.get("latest_pinned") is None:
        return need([f"endpoint_id clarification: '{endpoint_id}' is not a pinned endpoint"],
                    "Cannot validate or correct without knowing the endpoint.")
    if snap.get("stale"):
        return need([f"schema snapshot confirmation: case pins {version}, latest is {snap['latest_pinned']}"],
                    "A newer snapshot may change what is valid.")
    if webhook.get("present") and not webhook.get("verified"):
        return {"disposition": "escalation", "confidence": "high",
                "uncertainty": "Delivery result is distinct from queue outcome; needs engineering triage.",
                "packet": _packet(case, inv, "Unverified webhook delivery — reject callback.",
                                  "The receiver accepted a callback that fails signature checks; "
                                  "fix by enforcing verification before trusting delivery.")}
    if webhook.get("present") and webhook.get("status") == "ERROR":
        return {"disposition": "escalation", "confidence": "high",
                "uncertainty": "Queue outcome and delivery result disagree; needs engineering triage.",
                "packet": _packet(case, inv, "Webhook delivery ERROR against completed queue-item.",
                                  "The callback path fails while inference completed; "
                                  "fix by repairing delivery, not by rerunning inference.")}
    for q in queue:
        if q["status"] == "COMPLETED" and "error" in q["verdict"].lower() and "success" not in q["verdict"].lower():
            return {"disposition": "escalation", "confidence": "high",
                    "uncertainty": "Error fields must be read before any retry or correction.",
                    "packet": _packet(case, inv, f"Completed with error for {q['request_id']}.",
                                      f"The failure is in the error fields for {q['request_id']}; "
                                      "a payload change alone will not clear it.")}
    if errors and all(e["code"] in AUTO_FIXABLE for e in errors):
        fixed = _clamp_fix(case.get("payload") or {}, errors)
        remaining = validate_payload(fixed, endpoint_id, version)
        if not remaining:
            return {"disposition": "correction", "confidence": "high",
                    "uncertainty": "Correction is schema-valid; semantic fit still needs analyst approval.",
                    "corrected_payload": fixed}
    if errors:
        missing = [f"request payload.{e['field']} value (no evidenced value — not invented)"
                   for e in errors if e["code"] == "missing"]
        if missing:
            return need(missing, "Required values are absent and cannot be invented.")
    pending = [q for q in queue if q["status"] in ("IN_QUEUE", "IN_PROGRESS")]
    if pending:
        ids = ", ".join(q["request_id"] for q in pending)
        claim = "failure was reported" if "fail" in report else "no outcome is evidenced yet"
        return need([f"completion evidence for {ids} ({claim})"],
                    "A pending queue-item proves nothing about the inference outcome.")
    if not queue and not webhook.get("present"):
        missing = [f"request payload.{e['field']} value (no evidenced value — not invented)"
                   for e in errors if e["code"] == "missing"]
        missing += ["request_id", "timestamps"]
        return need(missing or ["request_id", "request payload", "timestamps"],
                    "No queue, webhook, or response evidence — abstaining.")
    return need(["request_id", "request payload", "timestamps"],
                "Evidence is contradictory or insufficient — abstaining.")
