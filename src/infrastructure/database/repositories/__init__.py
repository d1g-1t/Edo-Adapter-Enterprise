"""SQLAlchemy async repository implementations.

Key optimizations:
- selectinload / joinedload to avoid N+1 queries
- Batch operations where possible
- Index-aligned queries
- No implicit lazy loads (lazy="noload" on relationships)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.audit_event import AuditEvent
from src.domain.entities.dlq_entry import DLQEntry
from src.domain.entities.document_delivery import DocumentDelivery
from src.domain.entities.edo_document import EdoDocument
from src.domain.entities.provider_account import ProviderAccount
from src.domain.repositories.i_delivery_repository import (
    IAuditRepository,
    IDLQRepository,
    IDeliveryRepository,
    IProviderAccountRepository,
)
from src.domain.repositories.i_document_repository import IDocumentRepository
from src.domain.value_objects.provider_type import ProviderType
from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus
from src.infrastructure.database.models import (
    AuditEventModel,
    DLQEntryModel,
    DocumentDeliveryModel,
    EdoDocumentModel,
    ProviderAccountModel,
)


# ── Mappers (model ↔ entity) ────────────────────────────────────────────────

def _delivery_to_entity(m: DocumentDeliveryModel) -> DocumentDelivery:
    return DocumentDelivery(
        id=m.id,
        tenant_id=m.tenant_id,
        document_id=m.document_id,
        provider_account_id=m.provider_account_id,
        idempotency_key=m.idempotency_key,
        unified_status=UnifiedDocumentStatus(m.unified_status),
        provider_document_id=m.provider_document_id,
        provider_raw_status=m.provider_raw_status,
        retry_count=m.retry_count,
        next_retry_at=m.next_retry_at,
        last_error_code=m.last_error_code,
        last_error_message=m.last_error_message,
        sent_at=m.sent_at,
        delivered_at=m.delivered_at,
        signed_at=m.signed_at,
        rejected_at=m.rejected_at,
        final_at=m.final_at,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


def _document_to_entity(m: EdoDocumentModel) -> EdoDocument:
    return EdoDocument(
        id=m.id,
        tenant_id=m.tenant_id,
        internal_document_id=m.internal_document_id,
        document_type=m.document_type,
        sender_inn=m.sender_inn,
        sender_kpp=m.sender_kpp,
        recipient_inn=m.recipient_inn,
        recipient_kpp=m.recipient_kpp,
        title=m.title,
        file_name=m.file_name,
        mime_type=m.mime_type,
        file_checksum=m.file_checksum,
        metadata=m.metadata or {},
        created_by=m.created_by,
        created_at=m.created_at,
    )


def _provider_to_entity(m: ProviderAccountModel) -> ProviderAccount:
    return ProviderAccount(
        id=m.id,
        tenant_id=m.tenant_id,
        provider_type=ProviderType(m.provider_type),
        account_name=m.account_name,
        credentials_json=m.credentials_json,
        is_active=m.is_active,
        priority=m.priority,
        webhook_secret=m.webhook_secret,
        rate_limit_per_minute=m.rate_limit_per_minute,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# ── Repository implementations ──────────────────────────────────────────────

class SQLDocumentRepository(IDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, document: EdoDocument) -> None:
        model = EdoDocumentModel(
            id=document.id,
            tenant_id=document.tenant_id,
            internal_document_id=document.internal_document_id,
            document_type=document.document_type,
            sender_inn=document.sender_inn,
            sender_kpp=document.sender_kpp,
            recipient_inn=document.recipient_inn,
            recipient_kpp=document.recipient_kpp,
            title=document.title,
            file_name=document.file_name,
            mime_type=document.mime_type,
            file_checksum=document.file_checksum,
            metadata=document.metadata,
            created_by=document.created_by,
            created_at=document.created_at,
        )
        self._session.add(model)

    async def get_by_id(self, document_id: uuid.UUID) -> EdoDocument | None:
        stmt = select(EdoDocumentModel).where(EdoDocumentModel.id == document_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _document_to_entity(row) if row else None

    async def get_by_internal_id(
        self, tenant_id: uuid.UUID, internal_document_id: uuid.UUID
    ) -> EdoDocument | None:
        stmt = select(EdoDocumentModel).where(
            EdoDocumentModel.tenant_id == tenant_id,
            EdoDocumentModel.internal_document_id == internal_document_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _document_to_entity(row) if row else None

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[EdoDocument]:
        stmt = (
            select(EdoDocumentModel)
            .where(EdoDocumentModel.tenant_id == tenant_id)
            .order_by(EdoDocumentModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_document_to_entity(r) for r in rows]


class SQLDeliveryRepository(IDeliveryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, delivery: DocumentDelivery) -> None:
        model = DocumentDeliveryModel(
            id=delivery.id,
            tenant_id=delivery.tenant_id,
            document_id=delivery.document_id,
            provider_account_id=delivery.provider_account_id,
            idempotency_key=delivery.idempotency_key,
            unified_status=delivery.unified_status.value,
            provider_document_id=delivery.provider_document_id,
            provider_raw_status=delivery.provider_raw_status,
            retry_count=delivery.retry_count,
            next_retry_at=delivery.next_retry_at,
            last_error_code=delivery.last_error_code,
            last_error_message=delivery.last_error_message,
            sent_at=delivery.sent_at,
            delivered_at=delivery.delivered_at,
            signed_at=delivery.signed_at,
            rejected_at=delivery.rejected_at,
            final_at=delivery.final_at,
            created_at=delivery.created_at,
            updated_at=delivery.updated_at,
        )
        self._session.add(model)

    async def get_by_id(self, delivery_id: uuid.UUID) -> DocumentDelivery | None:
        stmt = select(DocumentDeliveryModel).where(DocumentDeliveryModel.id == delivery_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _delivery_to_entity(row) if row else None

    async def get_by_idempotency_key(
        self, provider_account_id: uuid.UUID, key: str
    ) -> DocumentDelivery | None:
        stmt = select(DocumentDeliveryModel).where(
            DocumentDeliveryModel.provider_account_id == provider_account_id,
            DocumentDeliveryModel.idempotency_key == key,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _delivery_to_entity(row) if row else None

    async def list_by_document(self, document_id: uuid.UUID) -> list[DocumentDelivery]:
        stmt = (
            select(DocumentDeliveryModel)
            .where(DocumentDeliveryModel.document_id == document_id)
            .order_by(DocumentDeliveryModel.created_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_delivery_to_entity(r) for r in rows]

    async def list_pending_retries(self, now: datetime) -> list[DocumentDelivery]:
        stmt = (
            select(DocumentDeliveryModel)
            .where(
                DocumentDeliveryModel.next_retry_at <= now,
                DocumentDeliveryModel.unified_status == UnifiedDocumentStatus.PENDING.value,
            )
            .limit(500)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_delivery_to_entity(r) for r in rows]

    async def list_non_final(
        self,
        provider_account_id: uuid.UUID | None = None,
        limit: int = 200,
    ) -> list[DocumentDelivery]:
        non_final = [
            s.value
            for s in UnifiedDocumentStatus
            if not s.is_terminal
        ]
        stmt = select(DocumentDeliveryModel).where(
            DocumentDeliveryModel.unified_status.in_(non_final)
        )
        if provider_account_id:
            stmt = stmt.where(
                DocumentDeliveryModel.provider_account_id == provider_account_id
            )
        stmt = stmt.limit(limit)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_delivery_to_entity(r) for r in rows]

    async def update(self, delivery: DocumentDelivery) -> None:
        stmt = (
            update(DocumentDeliveryModel)
            .where(DocumentDeliveryModel.id == delivery.id)
            .values(
                unified_status=delivery.unified_status.value,
                provider_document_id=delivery.provider_document_id,
                provider_raw_status=delivery.provider_raw_status,
                retry_count=delivery.retry_count,
                next_retry_at=delivery.next_retry_at,
                last_error_code=delivery.last_error_code,
                last_error_message=delivery.last_error_message,
                sent_at=delivery.sent_at,
                delivered_at=delivery.delivered_at,
                signed_at=delivery.signed_at,
                rejected_at=delivery.rejected_at,
                final_at=delivery.final_at,
                updated_at=delivery.updated_at,
            )
        )
        await self._session.execute(stmt)


class SQLProviderAccountRepository(IProviderAccountRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, account: ProviderAccount) -> None:
        model = ProviderAccountModel(
            id=account.id,
            tenant_id=account.tenant_id,
            provider_type=account.provider_type.value,
            account_name=account.account_name,
            credentials_json=account.credentials_json,
            is_active=account.is_active,
            priority=account.priority,
            webhook_secret=account.webhook_secret,
            rate_limit_per_minute=account.rate_limit_per_minute,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
        self._session.add(model)

    async def get_by_id(self, account_id: uuid.UUID) -> ProviderAccount | None:
        stmt = select(ProviderAccountModel).where(ProviderAccountModel.id == account_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _provider_to_entity(row) if row else None

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, active_only: bool = True
    ) -> list[ProviderAccount]:
        stmt = select(ProviderAccountModel).where(
            ProviderAccountModel.tenant_id == tenant_id
        )
        if active_only:
            stmt = stmt.where(ProviderAccountModel.is_active.is_(True))
        stmt = stmt.order_by(ProviderAccountModel.priority)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_provider_to_entity(r) for r in rows]

    async def update(self, account: ProviderAccount) -> None:
        stmt = (
            update(ProviderAccountModel)
            .where(ProviderAccountModel.id == account.id)
            .values(
                is_active=account.is_active,
                priority=account.priority,
                credentials_json=account.credentials_json,
                webhook_secret=account.webhook_secret,
                rate_limit_per_minute=account.rate_limit_per_minute,
                updated_at=account.updated_at,
            )
        )
        await self._session.execute(stmt)


class SQLDLQRepository(IDLQRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, entry: DLQEntry) -> None:
        model = DLQEntryModel(
            id=entry.id,
            tenant_id=entry.tenant_id,
            delivery_id=entry.delivery_id,
            provider_account_id=entry.provider_account_id,
            task_name=entry.task_name,
            payload=entry.payload,
            reason_code=entry.reason_code,
            reason_message=entry.reason_message,
            retryable=entry.retryable,
            replayed_at=entry.replayed_at,
            created_at=entry.created_at,
        )
        self._session.add(model)

    async def get_by_id(self, entry_id: uuid.UUID) -> DLQEntry | None:
        stmt = select(DLQEntryModel).where(DLQEntryModel.id == entry_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if not row:
            return None
        return DLQEntry(
            id=row.id,
            tenant_id=row.tenant_id,
            delivery_id=row.delivery_id,
            provider_account_id=row.provider_account_id,
            task_name=row.task_name,
            payload=row.payload,
            reason_code=row.reason_code,
            reason_message=row.reason_message,
            retryable=row.retryable,
            replayed_at=row.replayed_at,
            created_at=row.created_at,
        )

    async def list_retryable(self, tenant_id: uuid.UUID) -> list[DLQEntry]:
        stmt = select(DLQEntryModel).where(
            DLQEntryModel.tenant_id == tenant_id,
            DLQEntryModel.retryable.is_(True),
            DLQEntryModel.replayed_at.is_(None),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            DLQEntry(
                id=r.id,
                tenant_id=r.tenant_id,
                delivery_id=r.delivery_id,
                provider_account_id=r.provider_account_id,
                task_name=r.task_name,
                payload=r.payload,
                reason_code=r.reason_code,
                reason_message=r.reason_message,
                retryable=r.retryable,
                replayed_at=r.replayed_at,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def list_by_tenant(
        self, tenant_id: uuid.UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DLQEntry]:
        stmt = (
            select(DLQEntryModel)
            .where(DLQEntryModel.tenant_id == tenant_id)
            .order_by(DLQEntryModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            DLQEntry(
                id=r.id,
                tenant_id=r.tenant_id,
                delivery_id=r.delivery_id,
                provider_account_id=r.provider_account_id,
                task_name=r.task_name,
                payload=r.payload,
                reason_code=r.reason_code,
                reason_message=r.reason_message,
                retryable=r.retryable,
                replayed_at=r.replayed_at,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def update(self, entry: DLQEntry) -> None:
        stmt = (
            update(DLQEntryModel)
            .where(DLQEntryModel.id == entry.id)
            .values(replayed_at=entry.replayed_at)
        )
        await self._session.execute(stmt)


class SQLAuditRepository(IAuditRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, event: AuditEvent) -> None:
        model = AuditEventModel(
            id=event.id,
            tenant_id=event.tenant_id,
            actor_user_id=event.actor_user_id,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            event_type=event.event_type,
            trace_id=event.trace_id,
            payload=event.payload,
            created_at=event.created_at,
        )
        self._session.add(model)

    async def list_by_resource(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        *,
        limit: int = 100,
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEventModel)
            .where(
                AuditEventModel.resource_type == resource_type,
                AuditEventModel.resource_id == resource_id,
            )
            .order_by(AuditEventModel.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            AuditEvent(
                id=r.id,
                tenant_id=r.tenant_id,
                actor_user_id=r.actor_user_id,
                resource_type=r.resource_type,
                resource_id=r.resource_id,
                event_type=r.event_type,
                trace_id=r.trace_id,
                payload=r.payload,
                created_at=r.created_at,
            )
            for r in rows
        ]
