"""Live executor over the Gemini API free tier. No credits, no fal key.

The live-test flow keeps its shape (approval, caps, daily quota, request ID,
status, cost record) but executes the corrected prompt against a Gemini flash
model instead of fal's queue. Cost per run is $0; the daily quota guard stays
as an abuse meter. Only redacted payloads are sent, and the key stays in the
server environment. Transport is mocked in tests.
"""
import os
import time

from .llm import _generate, api_key, model


def submit(endpoint_id: str, payload: dict) -> dict:
    """Run the corrected prompt through Gemini. Raises on key/rate errors."""
    if not api_key():
        raise RuntimeError("LIVE_UNAVAILABLE: set GEMINI_API_KEY server-side")
    prompt = payload.get("prompt") or str(payload)[:2000]
    started = time.time()
    try:
        text = _generate({
            "system_instruction": {"parts": [{"text": (
                "You are validating an image-generation request for " + endpoint_id + ". "
                "Reply with JSON: {\"render\": \"one line describing what this would render as\"}.")}]},
            "contents": [{"parts": [{"text": str(prompt)[:2000]}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {"render": {"type": "STRING"}},
                    "required": ["render"],
                },
            },
        })
    except Exception as exc:
        raise RuntimeError(f"LIVE_UNAVAILABLE: {type(exc).__name__}") from exc
    return {"request_id": f"gem-{int(started)}",
            "status": "COMPLETED",
            "submitted_at": started,
            "completed_at": time.time(),
            "response_preview": text[:500],
            "model": model()}


def fetch_status(status_url: str | None = None) -> dict:
    """Free-tier runs finish synchronously; there is nothing to poll."""
    return {"status": "COMPLETED"}
