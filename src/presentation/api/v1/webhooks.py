from __future__ import annotations

import base64
import uuid

import structlog
from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from src.infrastructure.queue.tasks.process_webhook_task import process_webhook_task

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
log = structlog.get_logger(__name__)


async def _dispatch_webhook(
    request: Request,
    account_id: uuid.UUID,
) -> JSONResponse:
    body = await request.body()
    headers = dict(request.headers)

    body_b64 = base64.b64encode(body).decode()

    process_webhook_task.apply_async(
        kwargs={
            "account_id": str(account_id),
            "headers": headers,
            "body_b64": body_b64,
        },
        queue="edo.webhooks",
    )
    log.info("webhook_dispatched", account_id=str(account_id))
    return JSONResponse({"status": "queued"}, status_code=status.HTTP_202_ACCEPTED)


@router.post("/diadoc/{account_id}", status_code=status.HTTP_202_ACCEPTED)
async def diadoc_webhook(
    account_id: uuid.UUID,
    request: Request,
) -> JSONResponse:
    return await _dispatch_webhook(request, account_id)


@router.post("/sbis/{account_id}", status_code=status.HTTP_202_ACCEPTED)
async def sbis_webhook(
    account_id: uuid.UUID,
    request: Request,
) -> JSONResponse:
    return await _dispatch_webhook(request, account_id)


@router.post("/kontur-edo/{account_id}", status_code=status.HTTP_202_ACCEPTED)
async def kontur_webhook(
    account_id: uuid.UUID,
    request: Request,
) -> JSONResponse:
    return await _dispatch_webhook(request, account_id)
