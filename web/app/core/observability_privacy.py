from __future__ import annotations

import re
from typing import Any


_EMAIL_RE = re.compile(r"(?P<user>[A-Z0-9._%+\-]{1,64})@(?P<domain>[A-Z0-9.\-]+\.[A-Z]{2,})", re.IGNORECASE)
_AUTH_HEADER_RE = re.compile(r"\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=\-]+", re.IGNORECASE)
_COOKIE_PAIR_RE = re.compile(r"(?P<name>[A-Za-z0-9_\-]{2,64})=(?P<value>[^;,\s]{4,})")
_LONG_TOKEN_RE = re.compile(r"\b[A-F0-9]{24,}\b", re.IGNORECASE)
_SENSITIVE_KEYWORDS = (
    "authorization",
    "cookie",
    "csrf",
    "email",
    "password",
    "secret",
    "session",
    "token",
)
_PROTECTED_HEADER_NAMES = (
    "authorization",
    "cookie",
    "set-cookie",
    "x-csrf-token",
    "x-api-key",
)


def protected_header_names() -> tuple[str, ...]:
    return _PROTECTED_HEADER_NAMES


def _mask_email(value: str) -> str:
    return _EMAIL_RE.sub(lambda match: f"{match.group('user')[:1]}***@{match.group('domain')}", value)


def _mask_inline_secrets(value: str) -> str:
    sanitized = _AUTH_HEADER_RE.sub(lambda match: f"{match.group(1)} [redacted]", value)
    sanitized = _COOKIE_PAIR_RE.sub(lambda match: f"{match.group('name')}=[redacted]", sanitized)
    sanitized = _LONG_TOKEN_RE.sub("[redacted]", sanitized)
    return sanitized


def _mask_sensitive_keyed_text(value: str) -> str:
    if not value:
        return value
    normalized = value.strip()
    if not normalized:
        return normalized
    return "[redacted]"


def sanitize_observability_value(
    value: Any,
    *,
    key: str | None = None,
    depth: int = 0,
) -> Any:
    if depth >= 6:
        return "[truncated]"

    normalized_key = str(key or "").strip().lower()
    if value is None or isinstance(value, (bool, int, float)):
        return value

    if isinstance(value, dict):
        return {
            str(item_key): sanitize_observability_value(
                item_value,
                key=str(item_key),
                depth=depth + 1,
            )
            for item_key, item_value in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [
            sanitize_observability_value(item, key=normalized_key, depth=depth + 1)
            for item in value
        ]

    text = str(value)
    if any(keyword in normalized_key for keyword in _SENSITIVE_KEYWORDS):
        return _mask_sensitive_keyed_text(text)

    return _mask_inline_secrets(_mask_email(text))


__all__ = [
    "protected_header_names",
    "sanitize_observability_value",
]
