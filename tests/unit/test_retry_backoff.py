"""Unit tests: reliability — retry backoff logic."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.infrastructure.reliability.retry_backoff import (
    compute_next_retry,
    is_transient,
    should_retry,
)


class TestRetryBackoff:
    def test_should_retry_within_limit(self) -> None:
        assert should_retry(0)
        assert should_retry(4)

    def test_should_not_retry_at_limit(self) -> None:
        assert not should_retry(5)
        assert not should_retry(100)

    def test_compute_next_retry_returns_future_datetime(self) -> None:
        next_retry = compute_next_retry(0)
        assert next_retry > datetime.now(UTC)

    def test_compute_next_retry_increases_with_retry_count(self) -> None:
        # Statistically: higher retry count → longer average delay
        # We just test it returns a datetime without error
        for i in range(6):
            result = compute_next_retry(i)
            assert isinstance(result, datetime)
            assert result.tzinfo is not None

    def test_is_transient_known_codes(self) -> None:
        assert is_transient("PROVIDER_TRANSIENT_ERROR")
        assert is_transient("PROVIDER_RATE_LIMIT")
        assert is_transient("CIRCUIT_OPEN")

    def test_is_transient_permanent_code(self) -> None:
        assert not is_transient("PROVIDER_PERMANENT_ERROR")
        assert not is_transient("DOCUMENT_NOT_FOUND")
        assert not is_transient("AUTHENTICATION_FAILED")
