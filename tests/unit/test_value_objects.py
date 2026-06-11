"""Unit tests: domain value objects."""

from __future__ import annotations

import pytest

from src.domain.value_objects.inn import INN, KPP
from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus


class TestINN:
    """INN validation — 10-digit legal entity, 12-digit individual."""

    def test_valid_10_digit_inn(self) -> None:
        # Sberbank's INN
        inn = INN("7707083893")
        assert inn.value == "7707083893"

    def test_valid_12_digit_inn(self) -> None:
        # Generic valid 12-digit INN (checksum passes)
        inn = INN("500100732259")
        assert inn.value == "500100732259"

    def test_invalid_length_raises(self) -> None:
        with pytest.raises(ValueError, match="10 or 12"):
            INN("123")

    def test_invalid_checksum_raises(self) -> None:
        with pytest.raises(ValueError, match="checksum"):
            INN("7707083890")  # Last digit wrong

    def test_equality(self) -> None:
        a = INN("7707083893")
        b = INN("7707083893")
        assert a == b
        assert hash(a) == hash(b)

    def test_str_representation(self) -> None:
        inn = INN("7707083893")
        assert str(inn) == "7707083893"


class TestKPP:
    def test_valid_kpp(self) -> None:
        kpp = KPP("770701001")
        assert kpp.value == "770701001"

    def test_invalid_kpp_length(self) -> None:
        with pytest.raises(ValueError, match="9 digits"):
            KPP("12345")

    def test_invalid_kpp_non_numeric(self) -> None:
        with pytest.raises(ValueError, match="9 digits"):
            KPP("12345678X")


class TestUnifiedDocumentStatus:
    def test_terminal_statuses(self) -> None:
        assert UnifiedDocumentStatus.SIGNED.is_terminal
        assert UnifiedDocumentStatus.REJECTED.is_terminal
        assert UnifiedDocumentStatus.CANCELLED.is_terminal
        assert UnifiedDocumentStatus.FAILED.is_terminal

    def test_non_terminal_statuses(self) -> None:
        assert not UnifiedDocumentStatus.PENDING.is_terminal
        assert not UnifiedDocumentStatus.SENT.is_terminal
        assert not UnifiedDocumentStatus.DELIVERED.is_terminal

    def test_retryable_statuses(self) -> None:
        assert UnifiedDocumentStatus.PENDING.is_retryable
        assert UnifiedDocumentStatus.SENDING.is_retryable
        assert UnifiedDocumentStatus.FAILED.is_retryable

    def test_non_retryable_statuses(self) -> None:
        assert not UnifiedDocumentStatus.SIGNED.is_retryable
        assert not UnifiedDocumentStatus.DELIVERED.is_retryable
