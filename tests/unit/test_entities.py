"""Unit tests: domain entities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.domain.entities.document_delivery import DocumentDelivery
from src.domain.entities.edo_document import EdoDocument
from src.domain.entities.provider_account import ProviderAccount
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus


class TestEdoDocument:
    def test_create_computes_checksum(self) -> None:
        doc = EdoDocument.create(
            tenant_id=uuid.uuid4(),
            internal_document_id=uuid.uuid4(),
            document_type="INVOICE",
            sender_inn="7707083893",
            sender_kpp=None,
            recipient_inn="7707083893",
            recipient_kpp=None,
            title="Test Invoice",
            file_name="invoice.xml",
            mime_type="application/xml",
            file_bytes=b"<invoice>test</invoice>",
            created_by=uuid.uuid4(),
        )
        assert len(doc.file_checksum) == 64  # SHA-256 hex
        assert doc.id is not None
        assert doc.created_at.tzinfo is not None  # UTC-aware

    def test_document_is_immutable(self) -> None:
        doc = EdoDocument.create(
            tenant_id=uuid.uuid4(),
            internal_document_id=uuid.uuid4(),
            document_type="INVOICE",
            sender_inn="7707083893",
            sender_kpp=None,
            recipient_inn="7707083893",
            recipient_kpp=None,
            title="Test",
            file_name="test.xml",
            mime_type="text/xml",
            file_bytes=b"test",
            created_by=uuid.uuid4(),
        )
        with pytest.raises((AttributeError, TypeError, Exception)):
            doc.title = "Modified"  # type: ignore


class TestDocumentDelivery:
    def _make_delivery(self) -> DocumentDelivery:
        return DocumentDelivery.create(
            tenant_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            provider_account_id=uuid.uuid4(),
            idempotency_key="test-key",
        )

    def test_initial_status_is_pending(self) -> None:
        d = self._make_delivery()
        assert d.unified_status == UnifiedDocumentStatus.PENDING
        assert d.retry_count == 0

    def test_status_transitions(self) -> None:
        d = self._make_delivery()
        d.mark_sending()
        assert d.unified_status == UnifiedDocumentStatus.SENDING

        d.mark_sent("PROV-123")
        assert d.unified_status == UnifiedDocumentStatus.SENT
        assert d.provider_document_id == "PROV-123"
        assert d.sent_at is not None

        d.mark_delivered()
        assert d.unified_status == UnifiedDocumentStatus.DELIVERED

        d.mark_signed()
        assert d.unified_status == UnifiedDocumentStatus.SIGNED
        assert d.is_terminal

    def test_mark_failed(self) -> None:
        d = self._make_delivery()
        d.mark_failed("PROVIDER_TRANSIENT_ERROR", "Timeout")
        assert d.unified_status == UnifiedDocumentStatus.FAILED
        assert d.last_error_code == "PROVIDER_TRANSIENT_ERROR"
        assert d.is_terminal

    def test_schedule_retry(self) -> None:
        d = self._make_delivery()
        d.mark_failed("PROVIDER_TRANSIENT_ERROR", "Timeout")
        next_retry = datetime.now(UTC)
        d.schedule_retry(next_retry)
        assert d.retry_count == 1
        assert d.next_retry_at == next_retry
        assert d.unified_status == UnifiedDocumentStatus.PENDING


class TestProviderAccount:
    def test_create(self) -> None:
        acc = ProviderAccount.create(
            tenant_id=uuid.uuid4(),
            provider_type=ProviderType.STUB,
            account_name="test-stub",
            credentials_json={"webhook_secret": "secret"},
        )
        assert acc.is_active
        assert acc.provider_type == ProviderType.STUB
        assert acc.priority == 100

    def test_activate_deactivate(self) -> None:
        acc = ProviderAccount.create(
            tenant_id=uuid.uuid4(),
            provider_type=ProviderType.STUB,
            account_name="test",
            credentials_json={},
        )
        acc.deactivate()
        assert not acc.is_active
        acc.activate()
        assert acc.is_active
