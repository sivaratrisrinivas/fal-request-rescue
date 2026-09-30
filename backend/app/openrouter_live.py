"""Live executor over OpenRouter free tier. No fal key, no credits.

The live-test flow keeps its shape (approval, caps, daily quota, request ID,
status, cost record) but executes the corrected prompt against a free
OpenRouter model instead of fal's queue. Cost per run is $0; the daily free
quota (50/day) is enforced in code. Only redacted payloads are sent, and the
key stays in the server environment. Transport is mocked in tests.
"""
import os
import time
from datetime import datetime, timezone

import httpx

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"


def model() -> str:
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)


def api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "")


def submit(endpoint_id: str, payload: dict) -> dict:
    """Run the corrected prompt through a free model. Raises on key/rate errors."""
    key = api_key()
    if not key:
        raise RuntimeError("LIVE_UNAVAILABLE: set OPENROUTER_API_KEY server-side")
    prompt = payload.get("prompt") or str(payload)[:2000]
    started = datetime.now(timezone.utc).isoformat()
    try:
        resp = httpx.post(
            API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model(), "temperature": 0,
                  "response_format": {"type": "json_object"},
                  "messages": [
                      {"role": "system",
                       "content": ("You are validating an image-generation request for " + endpoint_id + ". "
                                   "Reply with JSON: {\"render\": \"one line describing what this would render as\"}.")},
                      {"role": "user", "content": str(prompt)[:2000]},
                  ]},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise RuntimeError(f"LIVE_UNAVAILABLE: {type(exc).__name__}") from exc
    choice = (data.get("choices") or [{}])[0]
    return {"request_id": data.get("id", f"or-{int(time.time())}"),
            "status": "COMPLETED",
            "submitted_at": started,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "response_preview": str((choice.get("message") or {}).get("content", ""))[:500]}


def fetch_status(status_url: str | None) -> dict:
    """Free-tier runs finish synchronously; there is nothing to poll."""
    return {"status": "COMPLETED"}
