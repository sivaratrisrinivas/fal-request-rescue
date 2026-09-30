"""Retry policy. Cites documented behavior; caps attempts in code."""
import os

_DEFAULT_CAP = int(os.environ.get("RETRY_MAX_ATTEMPTS", "3"))

_POLICIES = {
    "RATE_LIMIT": (True, "Rate-limited: back off and retry the same request.", _DEFAULT_CAP),
    "TIMEOUT": (True, "Timeout: check request status first, then retry the same request.", _DEFAULT_CAP),
    "QUEUE_FULL": (True, "Queue full: back off and retry the same request.", _DEFAULT_CAP),
    "SERVER_ERROR": (True, "Server error: retry the same request.", _DEFAULT_CAP),
    "UNAVAILABLE": (True, "Service unavailable: back off and retry.", _DEFAULT_CAP),
}


def classify(error_type: str | None) -> dict:
    """Non-retryable by default: malformed input is corrected or escalated, never looped."""
    entry = _POLICIES.get(str(error_type or "").upper())
    if entry is None:
        return {"retryable": False,
                "policy": "Not retryable: correct the payload or escalate. No retry loop.",
                "max_attempts": 1}
    retryable, policy, cap = entry
    return {"retryable": retryable, "policy": policy, "max_attempts": min(cap, _DEFAULT_CAP)}
