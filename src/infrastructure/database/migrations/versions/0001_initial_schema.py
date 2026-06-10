"""Initial schema: all tables for EDO Adapter Enterprise.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tenants ────────────────────────────────────────────────────────────
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("inn", sa.String(12), nullable=False, unique=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    )

    # ── api_users ──────────────────────────────────────────────────────────
    op.create_table(
        "api_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_api_users_tenant_id", "api_users", ["tenant_id"])
    op.create_index(
        "ix_api_users_tenant_email", "api_users", ["tenant_id", "email"], unique=True
    )

    # ── provider_accounts ──────────────────────────────────────────────────
    op.create_table(
        "provider_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column(
            "credentials", postgresql.JSONB, nullable=False, server_default="{}"
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_provider_accounts_tenant_id", "provider_accounts", ["tenant_id"]
    )

    # ── edo_documents ──────────────────────────────────────────────────────
    op.create_table(
        "edo_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("internal_id", sa.String(256), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(128), nullable=False),
        sa.Column("sender_inn", sa.String(12), nullable=False),
        sa.Column("receiver_inn", sa.String(12), nullable=False),
        sa.Column("filename", sa.String(512), nullable=True),
        sa.Column("content_type", sa.String(128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("sha256_checksum", sa.String(64), nullable=True),
        sa.Column("extra_meta", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_edo_documents_tenant_id", "edo_documents", ["tenant_id"])
    op.create_index(
        "ix_edo_documents_tenant_internal",
        "edo_documents",
        ["tenant_id", "internal_id"],
        unique=True,
    )

    # ── document_deliveries ────────────────────────────────────────────────
    op.create_table(
        "document_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider_account_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("provider_document_id", sa.String(256), nullable=True),
        sa.Column("provider_status", sa.String(128), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("raw_response", postgresql.JSONB, nullable=True),
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
        sa.ForeignKeyConstraint(
            ["document_id"], ["edo_documents.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["provider_account_id"], ["provider_accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "document_id", "provider_account_id", name="uq_delivery_document_account"
        ),
    )
    op.create_index(
        "ix_document_deliveries_document_id",
        "document_deliveries",
        ["document_id"],
    )
    op.create_index(
        "ix_document_deliveries_non_terminal",
        "document_deliveries",
        ["status", "next_retry_at"],
        postgresql_where=sa.text(
            "status NOT IN ('delivered','signed','rejected','cancelled','failed')"
        ),
    )

    # ── incoming_documents ─────────────────────────────────────────────────
    op.create_table(
        "incoming_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider_account_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("provider_document_id", sa.String(256), nullable=False),
        sa.Column("sender_inn", sa.String(12), nullable=True),
        sa.Column("sender_name", sa.String(512), nullable=True),
        sa.Column("document_type", sa.String(128), nullable=True),
        sa.Column("document_date", sa.Date, nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provider_account_id"], ["provider_accounts.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "provider_document_id",
            "provider_account_id",
            name="uq_incoming_provider_doc_account",
        ),
    )

    # ── webhook_events ─────────────────────────────────────────────────────
    op.create_table(
        "webhook_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider_account_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("provider_event_id", sa.String(256), nullable=True),
        sa.Column("event_type", sa.String(128), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB, nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["provider_account_id"], ["provider_accounts.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_webhook_events_provider_account_id",
        "webhook_events",
        ["provider_account_id"],
    )

    # ── dlq_entries ────────────────────────────────────────────────────────
    op.create_table(
        "dlq_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("is_retryable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_snapshot", postgresql.JSONB, nullable=True),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replayed_by", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["delivery_id"], ["document_deliveries.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_dlq_entries_retryable",
        "dlq_entries",
        ["is_retryable", "next_retry_at"],
        postgresql_where=sa.text("replayed_at IS NULL"),
    )

    # ── provider_health_snapshots ──────────────────────────────────────────
    op.create_table(
        "provider_health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_account_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("is_healthy", sa.Boolean, nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("circuit_state", sa.String(16), nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_account_id"], ["provider_accounts.id"], ondelete="CASCADE"
        ),
    )

    # ── audit_events ───────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("trace_id", sa.String(128), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["api_users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "idx_audit_events_resource",
        "audit_events",
        ["resource_type", "resource_id", "created_at"],
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])


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
