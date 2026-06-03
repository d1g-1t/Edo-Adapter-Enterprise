from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus


@dataclass
class DocumentDelivery:
    id: uuid.UUID
    tenant_id: uuid.UUID
    document_id: uuid.UUID
    provider_account_id: uuid.UUID
    idempotency_key: str
    unified_status: UnifiedDocumentStatus
    provider_document_id: str | None = None
    provider_raw_status: str | None = None
    retry_count: int = 0
    next_retry_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    signed_at: datetime | None = None
    rejected_at: datetime | None = None
    final_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        provider_account_id: uuid.UUID,
        idempotency_key: str,
    ) -> DocumentDelivery:
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            document_id=document_id,
            provider_account_id=provider_account_id,
            idempotency_key=idempotency_key,
            unified_status=UnifiedDocumentStatus.PENDING,
        )

    def mark_sending(self) -> None:
        self.unified_status = UnifiedDocumentStatus.SENDING
        self.updated_at = datetime.now(UTC)

    def mark_sent(self, provider_document_id: str) -> None:
        self.unified_status = UnifiedDocumentStatus.SENT
        self.provider_document_id = provider_document_id
        self.sent_at = datetime.now(UTC)
        self.updated_at = self.sent_at

    def mark_delivered(self) -> None:
        self.unified_status = UnifiedDocumentStatus.DELIVERED
        self.delivered_at = datetime.now(UTC)
        self.updated_at = self.delivered_at

    def mark_signed(self) -> None:
        self.unified_status = UnifiedDocumentStatus.SIGNED
        self.signed_at = datetime.now(UTC)
        self.final_at = self.signed_at
        self.updated_at = self.signed_at

    def mark_rejected(self) -> None:
        self.unified_status = UnifiedDocumentStatus.REJECTED
        self.rejected_at = datetime.now(UTC)
        self.final_at = self.rejected_at
        self.updated_at = self.rejected_at

    def mark_failed(self, error_code: str, error_message: str) -> None:
        self.unified_status = UnifiedDocumentStatus.FAILED
        self.last_error_code = error_code
        self.last_error_message = error_message
        self.final_at = datetime.now(UTC)
        self.updated_at = self.final_at

    def schedule_retry(self, next_retry_at: datetime) -> None:
        self.retry_count += 1
        self.next_retry_at = next_retry_at
        self.unified_status = UnifiedDocumentStatus.PENDING
        self.updated_at = datetime.now(UTC)

    @property
    def is_terminal(self) -> bool:
        return self.unified_status.is_terminal
