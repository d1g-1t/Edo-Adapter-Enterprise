from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select

from src.infrastructure.database.models import AuditEventModel
from src.application.dto import AuditEventResponse, PaginatedResponse
from src.presentation.deps import DBSession, AuthUser

router = APIRouter(prefix="/audit", tags=["audit"])
log = structlog.get_logger(__name__)


def _to_response(row: AuditEventModel) -> AuditEventResponse:
    return AuditEventResponse(
        id=row.id,
        event_type=row.event_type,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        actor_user_id=row.actor_user_id,
        trace_id=row.trace_id,
        payload=row.payload or {},
        created_at=row.created_at,
    )


@router.get(
    "/documents/{document_id}/timeline",
    response_model=PaginatedResponse[AuditEventResponse],
)
async def document_audit_timeline(
    document_id: uuid.UUID,
    session: DBSession,
    current_user: AuthUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[AuditEventResponse]:
    stmt = (
        select(AuditEventModel)
        .where(
            AuditEventModel.resource_type == "document",
            AuditEventModel.resource_id == document_id,
            AuditEventModel.tenant_id == current_user.tenant_id,
        )
        .order_by(AuditEventModel.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await session.execute(stmt)).scalars())
    items = [_to_response(r) for r in rows]
    return PaginatedResponse(items=items, total=len(items), limit=limit, offset=offset)


@router.get(
    "/deliveries/{delivery_id}/timeline",
    response_model=PaginatedResponse[AuditEventResponse],
)
async def delivery_audit_timeline(
    delivery_id: uuid.UUID,
    session: DBSession,
    current_user: AuthUser,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[AuditEventResponse]:
    stmt = (
        select(AuditEventModel)
        .where(
            AuditEventModel.resource_type == "delivery",
            AuditEventModel.resource_id == delivery_id,
            AuditEventModel.tenant_id == current_user.tenant_id,
        )
        .order_by(AuditEventModel.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await session.execute(stmt)).scalars())
    items = [_to_response(r) for r in rows]
    return PaginatedResponse(items=items, total=len(items), limit=limit, offset=offset)
