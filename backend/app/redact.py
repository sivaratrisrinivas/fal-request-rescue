"""Secret redaction. Runs before save and before any model send."""
import json
import re

MARKER = "[REDACTED]"

_SENSITIVE_KEYS = {
    "api_key", "apikey", "api-key", "x-api-key", "fal_key", "fal-key",
    "password", "passwd", "secret", "token", "authorization", "auth",
    "client_secret", "access_token",
}

_PATTERNS = [
    re.compile(r"fal-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"sk-[A-Za-z0-9_\-]{6,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+\-/=]{6,}", re.IGNORECASE),
    re.compile(r"(?i)(password|passwd|secret)\s*[:=]\s*\S+"),
]


def _scrub_string(s: str) -> tuple[str, bool]:
    had = False
    out = s
    for pat in _PATTERNS:
        out, n = pat.subn(MARKER, out)
        if n:
            had = True
    return out, had


def redact_json(obj):
    """Deep-redact secrets. Returns (redacted_obj, had_secret)."""
    if isinstance(obj, dict):
        redacted = {}
        had = False
        for k, v in obj.items():
            if isinstance(k, str) and k.lower() in _SENSITIVE_KEYS:
                redacted[k] = MARKER
                had = True
            else:
                rv, h = redact_json(v)
                redacted[k] = rv
                had = had or h
        return redacted, had
    if isinstance(obj, list):
        redacted_list = []
        had = False
        for v in obj:
            rv, h = redact_json(v)
            redacted_list.append(rv)
            had = had or h
        return redacted_list, had
    if isinstance(obj, str):
        return _scrub_string(obj)
    return obj, False


def contains_secret(text: str) -> bool:
    return any(pat.search(text) for pat in _PATTERNS)


def redact_text(text: str) -> tuple[str, bool]:
    return _scrub_string(text)
