from __future__ import annotations

import asyncio
import structlog

from celery import shared_task
from sqlalchemy import select

from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.database.models import DocumentDeliveryModel, ProviderAccountModel
from src.infrastructure.providers.provider_factory import ProviderFactory
from src.infrastructure.reliability.circuit_breaker import CircuitBreaker
from src.domain.value_objects.unified_document_status import UnifiedDocumentStatus
from src.infrastructure.observability.metrics import DELIVERY_STATUS_TRANSITIONS
from src.infrastructure.cache.redis_client import get_redis

log = structlog.get_logger(__name__)

_TERMINAL = {s.value for s in UnifiedDocumentStatus if s.is_terminal}


async def _sync() -> dict[str, int]:
    stats = {"checked": 0, "updated": 0, "errors": 0}
    redis = await get_redis()

    async with AsyncSessionFactory() as session:
        stmt = (
            select(DocumentDeliveryModel, ProviderAccountModel)
            .join(
                ProviderAccountModel,
                DocumentDeliveryModel.provider_account_id == ProviderAccountModel.id,
            )
            .where(
                DocumentDeliveryModel.status.notin_(list(_TERMINAL)),
                DocumentDeliveryModel.provider_document_id.is_not(None),
                ProviderAccountModel.is_active.is_(True),
            )
        )
        rows = (await session.execute(stmt)).all()

        for delivery_row, account_row in rows:
            stats["checked"] += 1
            cb = CircuitBreaker(redis, str(account_row.id))
            try:
                async with cb.guard():
                    provider = ProviderFactory.create(
                        account_row.provider_type, account_row.credentials
                    )
                    result = await provider.get_document_status(
                        delivery_row.provider_document_id
                    )

                old_status = delivery_row.status
                delivery_row.status = result.unified_status.value
                if result.raw_status:
                    delivery_row.provider_status = result.raw_status

                if old_status != delivery_row.status:
                    stats["updated"] += 1
                    DELIVERY_STATUS_TRANSITIONS.labels(
                        provider=account_row.provider_type,
                        from_status=old_status,
                        to_status=delivery_row.status,
                    ).inc()
                    log.info(
                        "delivery_status_synced",
                        delivery_id=str(delivery_row.id),
                        old=old_status,
                        new=delivery_row.status,
                    )

                await cb.record_success()
            except Exception as exc:
                stats["errors"] += 1
                await cb.record_failure()
                log.warning(
                    "status_sync_error",
                    delivery_id=str(delivery_row.id),
                    error=str(exc),
                )

        await session.commit()

    return stats


@shared_task(
    name="edo.sync_statuses",
    queue="edo.sync",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def sync_statuses_task(self) -> None:  # type: ignore[override]
    stats = asyncio.get_event_loop().run_until_complete(_sync())
    log.info("sync_statuses_complete", **stats)
