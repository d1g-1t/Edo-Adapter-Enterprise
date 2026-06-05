from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class DLQEntry:

    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_id: uuid.UUID | None
    provider_account_id: uuid.UUID | None
    task_name: str
    payload: dict[str, object]
    reason_code: str
    reason_message: str
    retryable: bool
    replayed_at: datetime | None
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        task_name: str,
        payload: dict[str, object],
        reason_code: str,
        reason_message: str,
        retryable: bool = False,
        delivery_id: uuid.UUID | None = None,
        provider_account_id: uuid.UUID | None = None,
    ) -> DLQEntry:
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            delivery_id=delivery_id,
            provider_account_id=provider_account_id,
            task_name=task_name,
            payload=payload,
            reason_code=reason_code,
            reason_message=reason_message,
            retryable=retryable,
            replayed_at=None,
            created_at=datetime.now(UTC),
        )

    def mark_replayed(self) -> None:
        self.replayed_at = datetime.now(UTC)
