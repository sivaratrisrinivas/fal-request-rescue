"""Server-side OpenRouter adapter. Key stays in the environment.

Never imported by the frontend. Only redacted summaries are sent.
Tests monkeypatch `draft_disposition`; no network in tests.
"""
import os

import httpx
from pydantic import BaseModel, Field

from .investigate import ALLOWLIST

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-4-31b-it:free"


class ToolRejected(ValueError):
    """Model proposed a tool outside the fixed allowlist."""


class DraftSchema(BaseModel):
    disposition: str
    confidence: str = "medium"
    uncertainty: str = ""
    tool: str = "trace_normalize"
    missing: list[str] = Field(default_factory=list)
    detail: str = ""


def draft_disposition(summary: dict) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("LLM_UNAVAILABLE: set OPENROUTER_API_KEY server-side")
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    resp = httpx.post(
        API_URL,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system",
                 "content": ("Propose one disposition as JSON: disposition "
                             "(correction|need-information|escalation), confidence, "
                             "uncertainty, tool (one of: " + ", ".join(ALLOWLIST) + "), "
                             "missing[], detail. Never invent values or endpoints.")},
                {"role": "user", "content": __import__("json").dumps(summary)},
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"bad LLM envelope: {exc}") from exc
    draft = DraftSchema.model_validate_json(content)
    if draft.tool not in ALLOWLIST:
        raise ToolRejected(f"tool '{draft.tool}' outside allowlist")
    if draft.disposition not in ("correction", "need-information", "escalation"):
        raise ValueError(f"bad disposition '{draft.disposition}'")
    return draft.model_dump()
