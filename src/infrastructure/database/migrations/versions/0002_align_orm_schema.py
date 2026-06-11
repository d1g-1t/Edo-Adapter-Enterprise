"""Align database schema with current ORM models.

Revision ID: 0002_align_orm_schema
Revises: 0001_initial_schema
Create Date: 2026-06-10 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_align_orm_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("provider_health_snapshots")
    op.drop_table("dlq_entries")
    op.drop_table("webhook_events")
    op.drop_table("incoming_documents")
    op.drop_table("document_deliveries")
    op.drop_table("edo_documents")
    op.drop_table("provider_accounts")
    op.drop_table("api_users")
    op.drop_table("tenants")

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "api_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    op.create_index("ix_api_users_tenant_id", "api_users", ["tenant_id"])

    op.create_table(
        "provider_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=False),
        sa.Column("credentials_json", postgresql.JSONB, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("100")),
        sa.Column("webhook_secret", sa.String(255), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("tenant_id", "provider_type", "account_name"),
    )
    op.create_index("ix_provider_accounts_tenant_id", "provider_accounts", ["tenant_id"])

    op.create_table(
        "edo_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("internal_document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("sender_inn", sa.String(12), nullable=False),
        sa.Column("sender_kpp", sa.String(9), nullable=True),
        sa.Column("recipient_inn", sa.String(12), nullable=False),
        sa.Column("recipient_kpp", sa.String(9), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("file_checksum", sa.String(64), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["api_users.id"]),
        sa.UniqueConstraint("tenant_id", "internal_document_id"),
    )
    op.create_index("ix_edo_documents_tenant_id", "edo_documents", ["tenant_id"])

    op.create_table(
        "document_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_document_id", sa.String(255), nullable=True),
        sa.Column("unified_status", sa.String(64), nullable=False),
        sa.Column("provider_raw_status", sa.String(255), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.Column("last_error_message", sa.Text, nullable=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["edo_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_account_id"], ["provider_accounts.id"]),
        sa.UniqueConstraint("provider_account_id", "idempotency_key"),
        sa.UniqueConstraint("provider_account_id", "provider_document_id"),
    )
    op.create_index(
        "idx_document_deliveries_status",
        "document_deliveries",
        ["unified_status", "updated_at"],
    )
    op.create_index(
        "idx_document_deliveries_retry",
        "document_deliveries",
        ["next_retry_at"],
        postgresql_where=sa.text("next_retry_at IS NOT NULL"),
    )

    op.create_table(
        "incoming_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_document_id", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(64), nullable=False),
        sa.Column("sender_inn", sa.String(12), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False),
        sa.Column("unified_status", sa.String(64), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["provider_account_id"], ["provider_accounts.id"]),
        sa.UniqueConstraint("provider_account_id", "provider_document_id"),
    )
    op.create_index(
        "idx_incoming_documents_received",
        "incoming_documents",
        ["received_at"],
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("external_event_id", sa.String(255), nullable=True),
        sa.Column("signature_status", sa.String(32), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("headers", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("processed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["provider_account_id"], ["provider_accounts.id"]),
    )
    op.create_index(
        "idx_webhook_events_processed",
        "webhook_events",
        ["processed", "created_at"],
    )

    op.create_table(
        "dlq_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_name", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=False),
        sa.Column("reason_code", sa.String(128), nullable=False),
        sa.Column("reason_message", sa.Text, nullable=False),
        sa.Column("retryable", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["delivery_id"], ["document_deliveries.id"]),
        sa.ForeignKeyConstraint(["provider_account_id"], ["provider_accounts.id"]),
    )
    op.create_index(
        "idx_dlq_entries_created",
        "dlq_entries",
        ["created_at"],
    )

    op.create_table(
        "provider_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("health_status", sa.String(32), nullable=False),
        sa.Column("circuit_state", sa.String(32), nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("error_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["provider_account_id"], ["provider_accounts.id"]),
    )
    op.create_index(
        "idx_provider_health_checked",
        "provider_health_snapshots",
        ["provider_account_id", "checked_at"],
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["api_users.id"]),
    )
    op.create_index(
        "idx_audit_events_resource",
        "audit_events",
        ["resource_type", "resource_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("provider_health_snapshots")
    op.drop_table("dlq_entries")
    op.drop_table("webhook_events")
    op.drop_table("incoming_documents")
    op.drop_table("document_deliveries")
    op.drop_table("edo_documents")
    op.drop_table("provider_accounts")
    op.drop_table("api_users")
    op.drop_table("tenants")

