from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from src.application.dto import (
    DeliveryResponse,
    DocumentResponse,
    DocumentStatusResponse,
    RetryDeliveryRequest,
    SendDocumentRequest,
)
from src.domain.entities.document_delivery import DocumentDelivery
from src.domain.entities.edo_document import EdoDocument
from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus
from src.infrastructure.database.repositories import (
    SQLDeliveryRepository,
    SQLDocumentRepository,
    SQLProviderAccountRepository,
)
from src.infrastructure.queue.tasks.send_document_task import send_document
from src.presentation.deps import AuthUser, DBSession

router = APIRouter(prefix="/documents", tags=["documents"])


def _delivery_response(d: DocumentDelivery) -> DeliveryResponse:
    return DeliveryResponse(
        id=d.id,
        document_id=d.document_id,
        provider_account_id=d.provider_account_id,
        unified_status=d.unified_status.value,
        provider_document_id=d.provider_document_id,
        retry_count=d.retry_count,
        last_error_code=d.last_error_code,
        last_error_message=d.last_error_message,
        sent_at=d.sent_at,
        delivered_at=d.delivered_at,
        signed_at=d.signed_at,
        rejected_at=d.rejected_at,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


@router.post(
    "/send",
    response_model=DeliveryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def send_document_endpoint(
    body: SendDocumentRequest,
    current_user: AuthUser,
    db: DBSession,
    file: UploadFile = File(...),
) -> DeliveryResponse:
    doc_repo = SQLDocumentRepository(db)
    account_repo = SQLProviderAccountRepository(db)
    delivery_repo = SQLDeliveryRepository(db)

    existing = await doc_repo.get_by_internal_id(
        current_user.tenant_id, body.internal_document_id
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document already exists: {body.internal_document_id}",
        )

    account = await account_repo.get_by_id(body.provider_account_id)
    if not account or account.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider account not found")
    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Provider account inactive")

    file_bytes = await file.read()

    document = EdoDocument.create(
        tenant_id=current_user.tenant_id,
        internal_document_id=body.internal_document_id,
        document_type=body.document_type,
        sender_inn=body.sender_inn,
        sender_kpp=body.sender_kpp,
        recipient_inn=body.recipient_inn,
        recipient_kpp=body.recipient_kpp,
        title=body.title,
        file_name=file.filename or "document",
        mime_type=file.content_type or "application/octet-stream",
        file_bytes=file_bytes,
        created_by=current_user.user_id,
        metadata=body.metadata,
    )
    await doc_repo.save(document)

    idempotency_key = f"{document.id}:{account.id}"
    delivery = DocumentDelivery.create(
        tenant_id=current_user.tenant_id,
        document_id=document.id,
        provider_account_id=account.id,
        idempotency_key=idempotency_key,
    )
    await delivery_repo.save(delivery)

    send_document.apply_async(
        kwargs={
            "delivery_id": str(delivery.id),
            "file_bytes_hex": file_bytes.hex(),
        },
        queue="edo.send",
    )

    return _delivery_response(delivery)


@router.get("/", response_model=list[DocumentResponse])
async def list_documents(
    current_user: AuthUser,
    db: DBSession,
    offset: int = 0,
    limit: int = 50,
) -> list[DocumentResponse]:
    repo = SQLDocumentRepository(db)
    docs = await repo.list_by_tenant(current_user.tenant_id, offset=offset, limit=limit)
    return [
        DocumentResponse(
            id=d.id,
            tenant_id=d.tenant_id,
            internal_document_id=d.internal_document_id,
            document_type=d.document_type,
            sender_inn=d.sender_inn,
            recipient_inn=d.recipient_inn,
            title=d.title,
            file_name=d.file_name,
            mime_type=d.mime_type,
            created_at=d.created_at,
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    current_user: AuthUser,
    db: DBSession,
) -> DocumentResponse:
    repo = SQLDocumentRepository(db)
    doc = await repo.get_by_id(document_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        internal_document_id=doc.internal_document_id,
        document_type=doc.document_type,
        sender_inn=doc.sender_inn,
        recipient_inn=doc.recipient_inn,
        title=doc.title,
        file_name=doc.file_name,
        mime_type=doc.mime_type,
        created_at=doc.created_at,
    )


@router.get("/{document_id}/deliveries", response_model=list[DeliveryResponse])
async def list_deliveries(
    document_id: uuid.UUID,
    current_user: AuthUser,
    db: DBSession,
) -> list[DeliveryResponse]:
    doc_repo = SQLDocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delivery_repo = SQLDeliveryRepository(db)
    deliveries = await delivery_repo.list_by_document(document_id)
    return [_delivery_response(d) for d in deliveries]


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    current_user: AuthUser,
    db: DBSession,
) -> DocumentStatusResponse:
    doc_repo = SQLDocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc or doc.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delivery_repo = SQLDeliveryRepository(db)
    deliveries = await delivery_repo.list_by_document(document_id)

    statuses = [d.unified_status for d in deliveries]
    best = (
        UnifiedDocumentStatus.SIGNED
        if UnifiedDocumentStatus.SIGNED in statuses
        else statuses[0]
        if statuses
        else UnifiedDocumentStatus.PENDING
    )

    return DocumentStatusResponse(
        document_id=document_id,
        unified_status=best.value,
        deliveries=[_delivery_response(d) for d in deliveries],
    )


@router.post("/{document_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_document(
    document_id: uuid.UUID,
    body: RetryDeliveryRequest,
    current_user: AuthUser,
    db: DBSession,
) -> dict[str, str]:
    delivery_repo = SQLDeliveryRepository(db)
    deliveries = await delivery_repo.list_by_document(document_id)
    failed = [d for d in deliveries if d.unified_status == UnifiedDocumentStatus.FAILED]
    if not failed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No failed deliveries found")

    for delivery in failed:
        if delivery.is_terminal and not body.force:
            continue
        delivery.unified_status = UnifiedDocumentStatus.PENDING
        delivery.next_retry_at = None
        await delivery_repo.update(delivery)
        send_document.apply_async(
            kwargs={
                "delivery_id": str(delivery.id),
                "file_bytes_hex": "",
            },
            queue="edo.send",
        )

    return {"status": "retry_dispatched"}
