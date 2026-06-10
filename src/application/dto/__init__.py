"""Application-layer DTOs for API request/response contracts.

All DTOs use Pydantic v2 for validation and serialisation.
They are the boundary between presentation and application layers.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


# ── Provider Account DTOs ──────────────────────────────────────────────────

class RegisterProviderAccountRequest(BaseModel):
    """Request to register a new provider account for a tenant."""

    provider_type: Literal["DIADOC", "SBIS", "KONTUR_EDO", "STUB"]
    account_name: str = Field(min_length=1, max_length=255)
    credentials_json: dict[str, Any]
    webhook_secret: str | None = None
    rate_limit_per_minute: int | None = Field(default=None, ge=1, le=10_000)
    priority: int = Field(default=100, ge=1, le=1000)


class ProviderAccountResponse(BaseModel):
    """Response schema for a provider account."""

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider_type: str
    account_name: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime


# ── Document / Send DTOs ───────────────────────────────────────────────────

class SendDocumentRequest(BaseModel):
    """Request to send a document via an EDO provider."""

    provider_account_id: uuid.UUID
    internal_document_id: uuid.UUID
    document_type: str = Field(min_length=1, max_length=64)
    sender_inn: str = Field(pattern=r"^\d{10}(\d{2})?$")
    sender_kpp: str | None = Field(default=None, pattern=r"^\d{9}$")
    recipient_inn: str = Field(pattern=r"^\d{10}(\d{2})?$")
    recipient_kpp: str | None = Field(default=None, pattern=r"^\d{9}$")
    title: str = Field(min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    internal_document_id: uuid.UUID
    document_type: str
    sender_inn: str
    recipient_inn: str
    title: str
    file_name: str
    mime_type: str
    created_at: datetime


# ── Delivery DTOs ──────────────────────────────────────────────────────────

class DeliveryResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    provider_account_id: uuid.UUID
    unified_status: str
    provider_document_id: str | None
    retry_count: int
    last_error_code: str | None
    last_error_message: str | None
    sent_at: datetime | None
    delivered_at: datetime | None
    signed_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RetryDeliveryRequest(BaseModel):
    reason: str | None = None
    force: bool = False


# ── Status DTOs ────────────────────────────────────────────────────────────

class DocumentStatusResponse(BaseModel):
    document_id: uuid.UUID
    unified_status: str
    deliveries: list[DeliveryResponse]


# ── Auth DTOs ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    tenant_id: uuid.UUID
    is_active: bool


# ── DLQ DTOs ──────────────────────────────────────────────────────────────

class DLQEntryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    delivery_id: uuid.UUID | None
    task_name: str
    reason_code: str
    reason_message: str
    retryable: bool
    replayed_at: datetime | None
    created_at: datetime


class ReplayDLQEntryRequest(BaseModel):
    force: bool = False


class ReplayBatchRequest(BaseModel):
    entry_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    force: bool = False


# ── Webhook DTOs ───────────────────────────────────────────────────────────

class WebhookProcessResponse(BaseModel):
    accepted: bool
    event_id: uuid.UUID | None = None


# ── Health DTOs ────────────────────────────────────────────────────────────

class ProviderHealthResponse(BaseModel):
    provider_account_id: uuid.UUID
    health_status: str
    circuit_state: str
    response_time_ms: int | None
    error_rate: float | None
    checked_at: datetime


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    version: str


# ── Incoming Document DTOs ─────────────────────────────────────────────────

class IncomingDocumentResponse(BaseModel):
    id: uuid.UUID
    provider_account_id: uuid.UUID
    provider_document_id: str
    document_type: str
    sender_inn: str
    sender_name: str | None
    file_name: str
    unified_status: str
    received_at: datetime
    created_at: datetime


# ── Audit DTOs ─────────────────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    resource_type: str
    resource_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    trace_id: str | None
    payload: dict[str, Any]
    created_at: datetime


# ── Pagination ─────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    """Generic paginated envelope."""

    items: list[Any]
    total: int
    offset: int
    limit: int
