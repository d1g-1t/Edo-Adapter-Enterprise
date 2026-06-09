from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from src.core.config import get_settings


def compute_next_retry(retry_count: int) -> datetime:
    s = get_settings()
    base = s.default_retry_base_seconds
    max_s = s.default_retry_max_seconds

    delay = min(base * (2 ** retry_count), max_s)
    jitter = random.uniform(0, delay)
    return datetime.now(UTC) + timedelta(seconds=jitter)


def should_retry(retry_count: int) -> bool:
    return retry_count < get_settings().default_retry_max_attempts


def is_transient(error_code: str) -> bool:
    transient_prefixes = {
        "PROVIDER_TRANSIENT_ERROR",
        "PROVIDER_RATE_LIMIT",
        "CIRCUIT_OPEN",
    }
    return any(error_code.startswith(p) for p in transient_prefixes)
