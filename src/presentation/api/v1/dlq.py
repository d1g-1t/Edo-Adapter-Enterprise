from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from src.application.dto import DLQEntryResponse, ReplayBatchRequest, ReplayDLQEntryRequest
from src.domain.entities.dlq_entry import DLQEntry
from src.infrastructure.database.repositories import SQLDLQRepository
from src.infrastructure.queue.tasks.send_document_task import send_document
from src.presentation.deps import AdminUser, AuthUser, DBSession

router = APIRouter(prefix="/dlq", tags=["dlq"])


def _to_response(e: DLQEntry) -> DLQEntryResponse:
    return DLQEntryResponse(
        id=e.id,
        tenant_id=e.tenant_id,
        delivery_id=e.delivery_id,
        task_name=e.task_name,
        reason_code=e.reason_code,
        reason_message=e.reason_message,
        retryable=e.retryable,
        replayed_at=e.replayed_at,
        created_at=e.created_at,
    )


@router.get("/", response_model=list[DLQEntryResponse])
async def list_dlq(
    current_user: AuthUser,
    db: DBSession,
    offset: int = 0,
    limit: int = 50,
) -> list[DLQEntryResponse]:
    repo = SQLDLQRepository(db)
    entries = await repo.list_by_tenant(current_user.tenant_id, offset=offset, limit=limit)
    return [_to_response(e) for e in entries]


@router.get("/{entry_id}", response_model=DLQEntryResponse)
async def get_dlq_entry(
    entry_id: uuid.UUID,
    current_user: AuthUser,
    db: DBSession,
) -> DLQEntryResponse:
    repo = SQLDLQRepository(db)
    entry = await repo.get_by_id(entry_id)
    if not entry or entry.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")
    return _to_response(entry)


@router.post("/{entry_id}/replay", status_code=status.HTTP_202_ACCEPTED)
async def replay_dlq_entry(
    entry_id: uuid.UUID,
    body: ReplayDLQEntryRequest,
    current_user: AdminUser,
    db: DBSession,
) -> dict[str, str]:
    repo = SQLDLQRepository(db)
    entry = await repo.get_by_id(entry_id)
    if not entry or entry.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")
    if not entry.retryable and not body.force:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Entry is not retryable. Use force=true to override.",
        )

    if entry.task_name == "send_document" and entry.delivery_id:
        send_document.apply_async(
            kwargs={"delivery_id": str(entry.delivery_id), "file_bytes_hex": ""},
            queue="edo.send",
        )

    entry.mark_replayed()
    await repo.update(entry)
    return {"status": "replayed"}


@router.post("/replay-batch", status_code=status.HTTP_202_ACCEPTED)
async def replay_batch(
    body: ReplayBatchRequest,
    current_user: AdminUser,
    db: DBSession,
) -> dict[str, int]:
    repo = SQLDLQRepository(db)
    replayed = 0
    for entry_id in body.entry_ids:
        entry = await repo.get_by_id(entry_id)
        if not entry or entry.tenant_id != current_user.tenant_id:
            continue
        if not entry.retryable and not body.force:
            continue
        if entry.task_name == "send_document" and entry.delivery_id:
            send_document.apply_async(
                kwargs={"delivery_id": str(entry.delivery_id), "file_bytes_hex": ""},
                queue="edo.send",
            )
        entry.mark_replayed()
        await repo.update(entry)
        replayed += 1
    return {"replayed": replayed}
