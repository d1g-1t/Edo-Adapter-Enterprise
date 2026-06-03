from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.domain.value_objects.provider_type import ProviderType


@dataclass
class ProviderAccount:

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: ProviderType
    account_name: str
    credentials_json: dict[str, object]
    is_active: bool
    priority: int
    webhook_secret: str | None
    rate_limit_per_minute: int | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        provider_type: ProviderType,
        account_name: str,
        credentials_json: dict[str, object],
        webhook_secret: str | None = None,
        rate_limit_per_minute: int | None = None,
        priority: int = 100,
    ) -> ProviderAccount:
        now = datetime.now(UTC)
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            provider_type=provider_type,
            account_name=account_name,
            credentials_json=credentials_json,
            is_active=True,
            priority=priority,
            webhook_secret=webhook_secret,
            rate_limit_per_minute=rate_limit_per_minute,
            created_at=now,
            updated_at=now,
        )

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = datetime.now(UTC)
