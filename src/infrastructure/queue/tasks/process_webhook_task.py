from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from celery import shared_task
from sqlalchemy import select

from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.database.models import (
    WebhookEventModel,
    DocumentDeliveryModel,
    ProviderAccountModel,
)
from src.infrastructure.providers.provider_factory import ProviderFactory
from src.infrastructure.observability.metrics import (
    WEBHOOK_RECEIVED_TOTAL,
    WEBHOOK_PROCESSING_ERRORS,
    DELIVERY_STATUS_TRANSITIONS,
)

log = structlog.get_logger(__name__)


async def _process(
    account_id: str,
    headers: dict[str, str],
    body_bytes: bytes,
) -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        account = (
            await session.execute(
                select(ProviderAccountModel).where(
                    ProviderAccountModel.id == uuid.UUID(account_id)
                )
            )
        ).scalar_one_or_none()

        if not account:
            log.error("webhook_account_not_found", account_id=account_id)
            return

        provider = ProviderFactory.create(account.provider_type, account.credentials)

        try:
            provider.validate_webhook(headers, body_bytes)
        except Exception as exc:
            WEBHOOK_PROCESSING_ERRORS.labels(
                provider=account.provider_type, reason="bad_signature"
            ).inc()
            log.warning("webhook_signature_invalid", account_id=account_id, error=str(exc))
            return

        events = provider.parse_webhook(headers, body_bytes)

        for event in events:
            exists = (
                await session.execute(
                    select(WebhookEventModel).where(
                        WebhookEventModel.provider_event_id == event.provider_event_id,
                        WebhookEventModel.provider_account_id == uuid.UUID(account_id),
                    )
                )
            ).scalar_one_or_none()

            if exists:
                log.debug(
                    "webhook_duplicate_skipped",
                    event_id=event.provider_event_id,
                )
                continue

            webhook_row = WebhookEventModel(
                id=uuid.uuid4(),
                tenant_id=account.tenant_id,
                provider_account_id=uuid.UUID(account_id),
                provider_event_id=event.provider_event_id,
                event_type=event.event_type,
                raw_payload=event.raw_payload,
                received_at=now,
                processed=True,
                processed_at=now,
            )
            session.add(webhook_row)
            WEBHOOK_RECEIVED_TOTAL.labels(
                provider=account.provider_type, event_type=event.event_type
            ).inc()

            if event.provider_document_id:
                delivery = (
                    await session.execute(
                        select(DocumentDeliveryModel).where(
                            DocumentDeliveryModel.provider_document_id
                            == event.provider_document_id,
                            DocumentDeliveryModel.provider_account_id
                            == uuid.UUID(account_id),
                        )
                    )
                ).scalar_one_or_none()

                if delivery and event.unified_status:
                    old_status = delivery.status
                    delivery.status = event.unified_status.value
                    DELIVERY_STATUS_TRANSITIONS.labels(
                        provider=account.provider_type,
                        from_status=old_status,
                        to_status=delivery.status,
                    ).inc()
                    log.info(
                        "webhook_status_updated",
                        delivery_id=str(delivery.id),
                        old=old_status,
                        new=delivery.status,
                    )

        await session.commit()


@shared_task(
    name="edo.process_webhook",
    queue="edo.webhooks",
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    acks_late=True,
)
def process_webhook_task(
    self,
    account_id: str,
    headers: dict[str, str],
    body_b64: str,
) -> None:
    import base64

    body_bytes = base64.b64decode(body_b64)
    try:
        asyncio.get_event_loop().run_until_complete(
            _process(account_id, headers, body_bytes)
        )
    except Exception as exc:
        log.warning("process_webhook_error", error=str(exc))
        raise self.retry(exc=exc)
