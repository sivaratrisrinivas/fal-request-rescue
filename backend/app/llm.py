"""Server-side Gemini adapter. Key stays in the environment.

Never imported by the frontend. Only redacted summaries are sent.
Tests monkeypatch `draft_disposition`; no network in tests.
"""
import os

import httpx
from pydantic import BaseModel, Field

from .investigate import ALLOWLIST

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-3.5-flash"


def model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "")


class ToolRejected(ValueError):
    """Model proposed a tool outside the fixed allowlist."""


class DraftSchema(BaseModel):
    disposition: str
    confidence: str = "medium"
    uncertainty: str = ""
    tool: str = "trace_normalize"
    missing: list[str] = Field(default_factory=list)
    detail: str = ""


def _generate(body: dict) -> str:
    key = api_key()
    if not key:
        raise RuntimeError("LLM_UNAVAILABLE: set GEMINI_API_KEY server-side")
    resp = httpx.post(
        f"{API_BASE}/models/{model()}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    resp.raise_for_status()
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError(f"bad Gemini envelope: {exc}") from exc


def draft_disposition(summary: dict) -> dict:
    text = _generate({
        "system_instruction": {"parts": [{"text": (
            "Propose one disposition as JSON: disposition "
            "(correction|need-information|escalation), confidence, "
            "uncertainty, tool (one of: " + ", ".join(ALLOWLIST) + "), "
            "missing[], detail. Never invent values or endpoints.")}]},
        "contents": [{"parts": [{"text": __import__("json").dumps(summary)}]}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "disposition": {"type": "STRING"},
                    "confidence": {"type": "STRING"},
                    "uncertainty": {"type": "STRING"},
                    "tool": {"type": "STRING"},
                    "missing": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "detail": {"type": "STRING"},
                },
                "required": ["disposition", "tool"],
            },
        },
    })
    draft = DraftSchema.model_validate_json(text)
    if draft.tool not in ALLOWLIST:
        raise ToolRejected(f"tool '{draft.tool}' outside allowlist")
    if draft.disposition not in ("correction", "need-information", "escalation"):
        raise ValueError(f"bad disposition '{draft.disposition}'")
    return draft.model_dump()
