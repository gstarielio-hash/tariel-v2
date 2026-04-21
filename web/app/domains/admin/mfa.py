"""Helpers mínimos de TOTP para o portal Admin-CEO."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote

_BASE32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def generate_totp_secret(*, length: int = 32) -> str:
    if length < 16:
        raise ValueError("Comprimento mínimo do segredo TOTP é 16.")
    return "".join(secrets.choice(_BASE32_ALPHABET) for _ in range(length))


def normalize_totp_secret(secret: str) -> str:
    valor = "".join(ch for ch in str(secret or "").strip().upper() if ch in _BASE32_ALPHABET)
    if not valor:
        raise ValueError("Segredo TOTP inválido.")
    return valor


def normalize_totp_code(code: str) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())[:8]


def _decode_secret(secret: str) -> bytes:
    secret_norm = normalize_totp_secret(secret)
    padded = secret_norm + "=" * ((8 - len(secret_norm) % 8) % 8)
    return base64.b32decode(padded, casefold=True)


def _hotp(secret: str, counter: int, *, digits: int = 6) -> str:
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", int(counter)), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    modulo = 10**digits
    return str(binary % modulo).zfill(digits)


def current_totp(secret: str, *, at_time: int | float | None = None, step_seconds: int = 30, digits: int = 6) -> str:
    timestamp = int(time.time() if at_time is None else at_time)
    counter = timestamp // step_seconds
    return _hotp(secret, counter, digits=digits)


def verify_totp(
    secret: str,
    code: str,
    *,
    at_time: int | float | None = None,
    step_seconds: int = 30,
    digits: int = 6,
    window: int = 1,
) -> bool:
    code_norm = normalize_totp_code(code)
    if len(code_norm) != digits:
        return False

    timestamp = int(time.time() if at_time is None else at_time)
    counter = timestamp // step_seconds
    for delta in range(-abs(window), abs(window) + 1):
        if hmac.compare_digest(_hotp(secret, counter + delta, digits=digits), code_norm):
            return True
    return False


def build_totp_otpauth_uri(secret: str, *, account_name: str, issuer: str = "Tariel Admin-CEO") -> str:
    secret_norm = normalize_totp_secret(secret)
    account = quote(str(account_name or "").strip() or "admin@tariel.ia", safe="")
    issuer_norm = quote(str(issuer or "Tariel Admin-CEO").strip(), safe="")
    return f"otpauth://totp/{issuer_norm}:{account}?secret={secret_norm}&issuer={issuer_norm}"


__all__ = [
    "build_totp_otpauth_uri",
    "current_totp",
    "generate_totp_secret",
    "normalize_totp_code",
    "normalize_totp_secret",
    "verify_totp",
]
