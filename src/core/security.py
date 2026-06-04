from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pyseto
from pyseto import Key

from src.core.config import get_settings


def _get_key() -> Key:
    settings = get_settings()
    raw = settings.paseto_secret_key.encode()
    key_bytes = raw[:32].ljust(32, b"\x00")
    return Key.new(version=4, purpose="local", key=key_bytes)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "iat": now.isoformat(),
        "exp": (now + timedelta(minutes=settings.access_token_ttl_minutes)).isoformat(),
        "type": "access",
        **(extra or {}),
    }
    token = pyseto.encode(_get_key(), payload)
    return token.decode() if isinstance(token, bytes) else str(token)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "iat": now.isoformat(),
        "exp": (now + timedelta(days=settings.refresh_token_ttl_days)).isoformat(),
        "type": "refresh",
    }
    token = pyseto.encode(_get_key(), payload)
    return token.decode() if isinstance(token, bytes) else str(token)


def decode_token(token: str) -> dict[str, Any]:
    try:
        decoded = pyseto.decode(_get_key(), token)
        payload: dict[str, Any] = decoded.payload
        exp_raw = payload.get("exp")
        if exp_raw is None:
            raise ValueError("Token has no expiry")
        exp = datetime.fromisoformat(str(exp_raw))
        if exp <= datetime.now(UTC):
            raise ValueError("Token expired")
        return payload
    except Exception as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
