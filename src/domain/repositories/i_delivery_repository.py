from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.audit_event import AuditEvent
from src.domain.entities.dlq_entry import DLQEntry
from src.domain.entities.document_delivery import DocumentDelivery
from src.domain.entities.provider_account import ProviderAccount


class IDeliveryRepository(ABC):

    @abstractmethod
    async def save(self, delivery: DocumentDelivery) -> None: ...

    @abstractmethod
    async def get_by_id(self, delivery_id: UUID) -> DocumentDelivery | None: ...

    @abstractmethod
    async def get_by_idempotency_key(
        self, provider_account_id: UUID, key: str
    ) -> DocumentDelivery | None: ...

    @abstractmethod
    async def list_by_document(self, document_id: UUID) -> list[DocumentDelivery]: ...

    @abstractmethod
    async def list_pending_retries(self, now: datetime) -> list[DocumentDelivery]: ...

    @abstractmethod
    async def list_non_final(
        self,
        provider_account_id: UUID | None = None,
        limit: int = 200,
    ) -> list[DocumentDelivery]: ...

    @abstractmethod
    async def update(self, delivery: DocumentDelivery) -> None: ...


class IProviderAccountRepository(ABC):

    @abstractmethod
    async def save(self, account: ProviderAccount) -> None: ...

    @abstractmethod
    async def get_by_id(self, account_id: UUID) -> ProviderAccount | None: ...

    @abstractmethod
    async def list_by_tenant(self, tenant_id: UUID, active_only: bool = True) -> list[ProviderAccount]: ...

    @abstractmethod
    async def update(self, account: ProviderAccount) -> None: ...


class IDLQRepository(ABC):

    @abstractmethod
    async def save(self, entry: DLQEntry) -> None: ...

    @abstractmethod
    async def get_by_id(self, entry_id: UUID) -> DLQEntry | None: ...

    @abstractmethod
    async def list_retryable(self, tenant_id: UUID) -> list[DLQEntry]: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DLQEntry]: ...

    @abstractmethod
    async def update(self, entry: DLQEntry) -> None: ...


class IAuditRepository(ABC):

    @abstractmethod
    async def save(self, event: AuditEvent) -> None: ...

    @abstractmethod
    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: UUID,
        *,
        limit: int = 100,
    ) -> list[AuditEvent]: ...
