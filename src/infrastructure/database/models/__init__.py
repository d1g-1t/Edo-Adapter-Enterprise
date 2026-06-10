"""SQLAlchemy ORM models matching the SQL schema exactly."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database.base import Base, TimestampMixin, UUIDPKMixin


class TenantModel(Base, UUIDPKMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    api_users: Mapped[list[ApiUserModel]] = relationship(
        "ApiUserModel", back_populates="tenant", lazy="noload"
    )
    provider_accounts: Mapped[list[ProviderAccountModel]] = relationship(
        "ProviderAccountModel", back_populates="tenant", lazy="noload"
    )


class ApiUserModel(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "api_users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    tenant: Mapped[TenantModel] = relationship("TenantModel", back_populates="api_users", lazy="joined")


class ProviderAccountModel(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "provider_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_type", "account_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rate_limit_per_minute: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tenant: Mapped[TenantModel] = relationship(
        "TenantModel", back_populates="provider_accounts", lazy="joined"
    )
    deliveries: Mapped[list[DocumentDeliveryModel]] = relationship(
        "DocumentDeliveryModel", back_populates="provider_account", lazy="noload"
    )
    health_snapshots: Mapped[list[ProviderHealthSnapshotModel]] = relationship(
        "ProviderHealthSnapshotModel", back_populates="provider_account", lazy="noload"
    )


class EdoDocumentModel(Base, UUIDPKMixin):
    __tablename__ = "edo_documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "internal_document_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    internal_document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sender_inn: Mapped[str] = mapped_column(String(12), nullable=False)
    sender_kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    recipient_inn: Mapped[str] = mapped_column(String(12), nullable=False)
    recipient_kpp: Mapped[str | None] = mapped_column(String(9), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    deliveries: Mapped[list[DocumentDeliveryModel]] = relationship(
        "DocumentDeliveryModel",
        back_populates="document",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    created_by_user: Mapped[ApiUserModel] = relationship(
        "ApiUserModel", foreign_keys=[created_by], lazy="joined"
    )


class DocumentDeliveryModel(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "document_deliveries"
    __table_args__ = (
        UniqueConstraint("provider_account_id", "idempotency_key"),
        UniqueConstraint("provider_account_id", "provider_document_id"),
        Index("idx_document_deliveries_status", "unified_status", "updated_at"),
        Index(
            "idx_document_deliveries_retry",
            "next_retry_at",
            postgresql_where="next_retry_at IS NOT NULL",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("edo_documents.id", ondelete="CASCADE"), nullable=False
    )
    provider_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_accounts.id"), nullable=False
    )
    provider_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unified_status: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_raw_status: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    document: Mapped[EdoDocumentModel] = relationship(
        "EdoDocumentModel", back_populates="deliveries", lazy="joined"
    )
    provider_account: Mapped[ProviderAccountModel] = relationship(
        "ProviderAccountModel", back_populates="deliveries", lazy="joined"
    )


class IncomingDocumentModel(Base, UUIDPKMixin):
    __tablename__ = "incoming_documents"
    __table_args__ = (
        UniqueConstraint("provider_account_id", "provider_document_id"),
        Index("idx_incoming_documents_received", "received_at", postgresql_using="btree"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    provider_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_accounts.id"), nullable=False
    )
    provider_document_id: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sender_inn: Mapped[str] = mapped_column(String(12), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    unified_status: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider_account: Mapped[ProviderAccountModel] = relationship(
        "ProviderAccountModel", lazy="joined"
    )


class WebhookEventModel(Base, UUIDPKMixin):
    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("idx_webhook_events_processed", "processed", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    provider_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_accounts.id"), nullable=False
    )
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    external_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    headers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DLQEntryModel(Base, UUIDPKMixin):
    __tablename__ = "dlq_entries"
    __table_args__ = (
        Index("idx_dlq_entries_created", "created_at", postgresql_using="btree"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    delivery_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_deliveries.id"), nullable=True
    )
    provider_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_accounts.id"), nullable=True
    )
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(128), nullable=False)
    reason_message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderHealthSnapshotModel(Base, UUIDPKMixin):
    __tablename__ = "provider_health_snapshots"
    __table_args__ = (
        Index(
            "idx_provider_health_checked",
            "provider_account_id",
            "checked_at",
            postgresql_using="btree",
        ),
    )

    provider_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_accounts.id"), nullable=False
    )
    health_status: Mapped[str] = mapped_column(String(32), nullable=False)
    circuit_state: Mapped[str] = mapped_column(String(32), nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    provider_account: Mapped[ProviderAccountModel] = relationship(
        "ProviderAccountModel", back_populates="health_snapshots", lazy="joined"
    )


class AuditEventModel(Base, UUIDPKMixin):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_events_resource", "resource_type", "resource_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_users.id"), nullable=True
    )
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
