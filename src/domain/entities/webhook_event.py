from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from src.domain.value_objects.delivery_status import WebhookSignatureStatus


@dataclass
class WebhookEvent:

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_account_id: uuid.UUID
    provider_type: str
    external_event_id: str | None
    signature_status: WebhookSignatureStatus
    payload: dict[str, object]
    headers: dict[str, str]
    processed: bool
    processed_at: datetime | None
    error_message: str | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        provider_account_id: uuid.UUID,
        provider_type: str,
        signature_status: WebhookSignatureStatus,
        payload: dict[str, object],
        headers: dict[str, str],
        external_event_id: str | None = None,
    ) -> WebhookEvent:
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider_account_id=provider_account_id,
            provider_type=provider_type,
            external_event_id=external_event_id,
            signature_status=signature_status,
            payload=payload,
            headers=headers,
            processed=False,
            processed_at=None,
            error_message=None,
            created_at=datetime.now(UTC),
        )

    def mark_processed(self) -> None:
        self.processed = True
        self.processed_at = datetime.now(UTC)

    def mark_failed(self, message: str) -> None:
        self.processed = False
        self.error_message = message
