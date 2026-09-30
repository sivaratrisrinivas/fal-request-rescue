"""Local live runner over Ollama. Free, open-source, no key, no account.

The live-test flow keeps its shape (approval, caps, request ID, status poll,
cost record) but executes against a local model instead of fal's queue, so the
paid-run plumbing is provable for $0. Cost estimates for local runs are 0.0.

Never imported by the frontend. Only redacted payloads are sent, and only to
the configured local host. Transport is mocked in tests.
"""
import os
import uuid
from datetime import datetime, timezone

import httpx

DEFAULT_MODEL = "gemma3:1b"


def host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def model() -> str:
    return os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)


def _prompt_for(endpoint_id: str, payload: dict) -> str:
    text = payload.get("prompt") or json_dumps(payload)
    return (f"You are validating an image-generation request for {endpoint_id}. "
            f"Reply with one short line describing what this prompt would render: {text}")


def json_dumps(payload: dict) -> str:
    import json
    return json.dumps(payload, sort_keys=True)[:2000]


def submit(endpoint_id: str, payload: dict) -> dict:
    """Run the prompt text locally. Raises on unreachable runner or HTTP error."""
    started = datetime.now(timezone.utc).isoformat()
    try:
        resp = httpx.post(
            f"{host()}/api/generate",
            json={"model": model(), "prompt": _prompt_for(endpoint_id, payload),
                  "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")
    except Exception as exc:
        raise RuntimeError(f"OLLAMA_UNREACHABLE at {host()}: {type(exc).__name__}") from exc
    return {"request_id": f"local-{uuid.uuid4().hex[:8]}",
            "status": "COMPLETED",
            "status_url": None,
            "submitted_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "response_preview": text[:500]}


def fetch_status(status_url: str | None) -> dict:
    """Local runs finish synchronously; there is nothing to poll."""
    return {"status": "COMPLETED"}
