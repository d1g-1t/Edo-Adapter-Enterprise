from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.entities.edo_document import EdoDocument


class IDocumentRepository(ABC):

    @abstractmethod
    async def save(self, document: EdoDocument) -> None: ...

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> EdoDocument | None: ...

    @abstractmethod
    async def get_by_internal_id(
        self, tenant_id: UUID, internal_document_id: UUID
    ) -> EdoDocument | None: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[EdoDocument]: ...
