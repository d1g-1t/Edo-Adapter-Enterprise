from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from src.application.interfaces.i_edo_provider import (
    IEDOProvider,
    IncomingDocumentData,
    SendResult,
    StatusResult,
    WebhookParseResult,
)
from src.core.logging import get_logger

logger = get_logger(__name__)

_DOCUMENTS: dict[str, dict[str, Any]] = {}
_SENT_AT: dict[str, datetime] = {}


class StubEDOProvider(IEDOProvider):

    def __init__(
        self,
        credentials: dict[str, Any] | None = None,
        simulate_latency_ms: int = 50,
    ) -> None:
        self._credentials = credentials or {}
        self._latency = simulate_latency_ms / 1000.0
        self._webhook_secret: str = self._credentials.get("webhook_secret", "stub-secret")
        self._auto_sign_secs: int = self._credentials.get("auto_sign_delay_seconds", 30)

    async def send_document(
        self,
        *,
        sender_inn: str,
        sender_kpp: str | None,
        recipient_inn: str,
        recipient_kpp: str | None,
        document_type: str,
        title: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        metadata: dict[str, Any],
    ) -> SendResult:
        await asyncio.sleep(self._latency)
        provider_doc_id = f"STUB-{uuid.uuid4().hex[:16].upper()}"
        _DOCUMENTS[provider_doc_id] = {
            "sender_inn": sender_inn,
            "recipient_inn": recipient_inn,
            "document_type": document_type,
            "title": title,
            "file_name": file_name,
            "mime_type": mime_type,
            "status": "SENT",
        }
        _SENT_AT[provider_doc_id] = datetime.now(UTC)
        logger.info("stub_provider.send", provider_document_id=provider_doc_id, title=title)
        return SendResult(provider_document_id=provider_doc_id, raw_status="SENT")

    async def get_document_status(self, provider_document_id: str) -> StatusResult:
        await asyncio.sleep(self._latency)
        doc = _DOCUMENTS.get(provider_document_id)
        if doc is None:
            return StatusResult(
                provider_document_id=provider_document_id,
                unified_status="UNKNOWN",
                raw_status="not_found",
                extra={},
            )
        sent_at = _SENT_AT.get(provider_document_id, datetime.now(UTC))
        age = (datetime.now(UTC) - sent_at).total_seconds()

        if age > self._auto_sign_secs:
            raw = "SIGNED"
            unified = "SIGNED"
        elif age > self._auto_sign_secs / 2:
            raw = "DELIVERED"
            unified = "DELIVERED"
        else:
            raw = "SENT"
            unified = "SENT"

        _DOCUMENTS[provider_document_id]["status"] = raw
        return StatusResult(
            provider_document_id=provider_document_id,
            unified_status=unified,
            raw_status=raw,
            extra={"age_seconds": age},
        )

    async def poll_incoming(
        self,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[IncomingDocumentData]:
        await asyncio.sleep(self._latency)
        # Generate 3 synthetic incoming documents
        results: list[IncomingDocumentData] = []
        for i in range(min(3, limit)):
            results.append(
                IncomingDocumentData(
                    provider_document_id=f"STUB-IN-{uuid.uuid4().hex[:12].upper()}",
                    document_type="INVOICE",
                    sender_inn="7707083893",
                    sender_name="ООО Ромашка",
                    file_name=f"invoice_{i + 1}.xml",
                    mime_type="application/xml",
                    unified_status="DELIVERED",
                    metadata={"stub": True, "index": i},
                    received_at=datetime.now(UTC) - timedelta(minutes=i * 5),
                )
            )
        return results

    async def validate_webhook(self, payload: bytes, headers: dict[str, str]) -> bool:
        sig_header = headers.get("x-stub-signature", "")
        if not sig_header:
            return True
        expected = hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, sig_header)

    async def parse_webhook(self, payload: dict[str, Any]) -> WebhookParseResult:
        return WebhookParseResult(
            external_event_id=payload.get("event_id"),
            provider_document_id=payload.get("document_id"),
            unified_status=payload.get("status"),
            raw_payload=payload,
        )

    async def health_check(self) -> tuple[bool, int]:
        start = datetime.now(UTC)
        await asyncio.sleep(self._latency)
        ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
        return True, ms
