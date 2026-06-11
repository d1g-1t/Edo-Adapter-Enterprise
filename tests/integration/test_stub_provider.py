"""Integration tests: Stub EDO provider."""

from __future__ import annotations

import pytest

from src.infrastructure.providers.stub.stub_provider import StubEDOProvider


class TestStubProvider:
    """These tests run against the in-memory Stub — no external services needed."""

    @pytest.fixture
    def provider(self) -> StubEDOProvider:
        return StubEDOProvider(
            credentials={"webhook_secret": "test-secret"},
            simulate_latency_ms=0,  # Fast for tests
        )

    async def test_send_document_returns_provider_id(self, provider: StubEDOProvider) -> None:
        result = await provider.send_document(
            sender_inn="7707083893",
            sender_kpp=None,
            recipient_inn="7707083893",
            recipient_kpp=None,
            document_type="INVOICE",
            title="Test Invoice",
            file_name="invoice.xml",
            mime_type="application/xml",
            file_bytes=b"<invoice/>",
            metadata={},
        )
        assert result.provider_document_id.startswith("STUB-")
        assert result.raw_status == "SENT"

    async def test_get_status_after_send(self, provider: StubEDOProvider) -> None:
        send_result = await provider.send_document(
            sender_inn="7707083893",
            sender_kpp=None,
            recipient_inn="7707083893",
            recipient_kpp=None,
            document_type="INVOICE",
            title="Status Test",
            file_name="doc.xml",
            mime_type="application/xml",
            file_bytes=b"<doc/>",
            metadata={},
        )
        status = await provider.get_document_status(send_result.provider_document_id)
        assert status.provider_document_id == send_result.provider_document_id
        assert status.unified_status in ("SENT", "DELIVERED", "SIGNED")

    async def test_get_status_unknown_document(self, provider: StubEDOProvider) -> None:
        status = await provider.get_document_status("NONEXISTENT-ID")
        assert status.unified_status == "UNKNOWN"

    async def test_poll_incoming_returns_documents(self, provider: StubEDOProvider) -> None:
        docs = await provider.poll_incoming(limit=5)
        assert len(docs) == 3  # Stub always returns 3
        for doc in docs:
            assert doc.sender_inn == "7707083893"
            assert doc.unified_status == "DELIVERED"

    async def test_health_check_returns_healthy(self, provider: StubEDOProvider) -> None:
        is_healthy, response_ms = await provider.health_check()
        assert is_healthy
        assert response_ms >= 0

    async def test_validate_webhook_no_signature_passes(self, provider: StubEDOProvider) -> None:
        result = await provider.validate_webhook(b'{"event": "test"}', {})
        assert result is True

    async def test_validate_webhook_valid_signature(self, provider: StubEDOProvider) -> None:
        import hashlib
        import hmac
        payload = b'{"event": "test"}'
        sig = hmac.new(b"test-secret", payload, hashlib.sha256).hexdigest()
        result = await provider.validate_webhook(payload, {"x-stub-signature": sig})
        assert result is True

    async def test_validate_webhook_invalid_signature(self, provider: StubEDOProvider) -> None:
        result = await provider.validate_webhook(
            b'{"event": "test"}',
            {"x-stub-signature": "invalid-signature"},
        )
        assert result is False

    async def test_parse_webhook(self, provider: StubEDOProvider) -> None:
        payload = {
            "event_id": "evt-123",
            "document_id": "STUB-DOC-456",
            "status": "SIGNED",
        }
        result = await provider.parse_webhook(payload)
        assert result.external_event_id == "evt-123"
        assert result.provider_document_id == "STUB-DOC-456"
        assert result.unified_status == "SIGNED"
