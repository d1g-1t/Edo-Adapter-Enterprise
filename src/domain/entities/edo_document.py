from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class EdoDocument:

    id: uuid.UUID
    tenant_id: uuid.UUID
    internal_document_id: uuid.UUID
    document_type: str
    sender_inn: str
    sender_kpp: str | None
    recipient_inn: str
    recipient_kpp: str | None
    title: str
    file_name: str
    mime_type: str
    file_checksum: str
    metadata: dict[str, object]
    created_by: uuid.UUID
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        internal_document_id: uuid.UUID,
        document_type: str,
        sender_inn: str,
        sender_kpp: str | None,
        recipient_inn: str,
        recipient_kpp: str | None,
        title: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        created_by: uuid.UUID,
        metadata: dict[str, object] | None = None,
    ) -> EdoDocument:
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            internal_document_id=internal_document_id,
            document_type=document_type,
            sender_inn=sender_inn,
            sender_kpp=sender_kpp,
            recipient_inn=recipient_inn,
            recipient_kpp=recipient_kpp,
            title=title,
            file_name=file_name,
            mime_type=mime_type,
            file_checksum=hashlib.sha256(file_bytes).hexdigest(),
            metadata=metadata or {},
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
