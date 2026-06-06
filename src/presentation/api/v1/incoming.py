from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from src.infrastructure.database.models import IncomingDocumentModel
from src.infrastructure.queue.tasks.poll_incoming_task import poll_incoming_task
from src.application.dto import IncomingDocumentResponse, PaginatedResponse
from src.presentation.deps import DBSession, AuthUser, AdminUser

router = APIRouter(prefix="/incoming", tags=["incoming"])


@router.get("/", response_model=PaginatedResponse[IncomingDocumentResponse])
async def list_incoming(
    session: DBSession,
    current_user: AuthUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[IncomingDocumentResponse]:
    stmt = (
        select(IncomingDocumentModel)
        .where(IncomingDocumentModel.tenant_id == current_user.tenant_id)
        .order_by(IncomingDocumentModel.received_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = list((await session.execute(stmt)).scalars())
    items = [_to_response(r) for r in rows]
    return PaginatedResponse(items=items, total=len(items), limit=limit, offset=offset)


@router.get("/{doc_id}", response_model=IncomingDocumentResponse)
async def get_incoming(
    doc_id: uuid.UUID,
    session: DBSession,
    current_user: AuthUser,
) -> IncomingDocumentResponse:
    row = (
        await session.execute(
            select(IncomingDocumentModel).where(
                IncomingDocumentModel.id == doc_id,
                IncomingDocumentModel.tenant_id == current_user.tenant_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _to_response(row)


@router.post("/poll", status_code=status.HTTP_202_ACCEPTED)
async def trigger_poll(
    current_user: AdminUser,
) -> dict[str, str]:
    poll_incoming_task.apply_async(queue="edo.sync")
    return {"status": "queued"}


def _to_response(row: IncomingDocumentModel) -> IncomingDocumentResponse:
    return IncomingDocumentResponse(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        provider_account_id=str(row.provider_account_id),
        provider_document_id=row.provider_document_id,
        sender_inn=row.sender_inn,
        sender_name=row.sender_name,
        document_type=row.document_type,
        document_date=row.document_date,
        received_at=row.received_at,
    )
