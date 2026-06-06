from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus


@dataclass
class IncomingDocument:

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_account_id: uuid.UUID
    provider_document_id: str
    document_type: str
    sender_inn: str
    sender_name: str | None
    file_name: str
    mime_type: str
    unified_status: UnifiedDocumentStatus
    metadata: dict[str, object]
    received_at: datetime
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        provider_account_id: uuid.UUID,
        provider_document_id: str,
        document_type: str,
        sender_inn: str,
        sender_name: str | None,
        file_name: str,
        mime_type: str,
        unified_status: UnifiedDocumentStatus,
        metadata: dict[str, object] | None = None,
        received_at: datetime | None = None,
    ) -> IncomingDocument:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider_account_id=provider_account_id,
            provider_document_id=provider_document_id,
            document_type=document_type,
            sender_inn=sender_inn,
            sender_name=sender_name,
            file_name=file_name,
            mime_type=mime_type,
            unified_status=unified_status,
            metadata=metadata or {},
            received_at=received_at or now,
            created_at=now,
        )
