"""Server-side fal queue adapter. FAL_API_KEY lives in the environment only.

Never imported by the frontend. The key is never logged, stored, or sent anywhere
except fal's queue API. Shape follows fal's queue docs (submit returns request_id
plus status_url; status is polled at that URL). Untested against live fal: no key
was available during the prototype, so live paths are covered with mocked transport.
"""
import os
from datetime import datetime, timezone

import httpx

QUEUE_BASE = "https://queue.fal.run"


def api_key() -> str:
    return os.environ.get("FAL_API_KEY", "")


def submit(endpoint_id: str, payload: dict) -> dict:
    key = api_key()
    if not key:
        raise RuntimeError("LIVE_UNAVAILABLE: set FAL_API_KEY server-side")
    resp = httpx.post(
        f"{QUEUE_BASE}/{endpoint_id}",
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"request_id": data["request_id"],
            "status": data.get("status", "IN_QUEUE"),
            "status_url": data.get("status_url"),
            "submitted_at": datetime.now(timezone.utc).isoformat()}


def fetch_status(status_url: str) -> dict:
    key = api_key()
    if not key:
        raise RuntimeError("LIVE_UNAVAILABLE: set FAL_API_KEY server-side")
    resp = httpx.get(status_url, headers={"Authorization": f"Key {key}"}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {"status": data.get("status", "UNKNOWN"), "raw": data}
