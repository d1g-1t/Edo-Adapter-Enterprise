from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select

from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.database.models import ProviderAccountModel, IncomingDocumentModel
from src.infrastructure.providers.provider_factory import ProviderFactory
from src.infrastructure.reliability.circuit_breaker import CircuitBreaker
from src.infrastructure.observability.metrics import INCOMING_DOCUMENTS_POLLED
from src.infrastructure.cache.redis_client import get_redis

log = structlog.get_logger(__name__)


async def _poll() -> dict[str, int]:
    stats = {"accounts": 0, "new_docs": 0, "errors": 0}
    redis = await get_redis()
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        stmt = select(ProviderAccountModel).where(
            ProviderAccountModel.is_active.is_(True)
        )
        accounts = list((await session.execute(stmt)).scalars())
        stats["accounts"] = len(accounts)

        for account in accounts:
            cb = CircuitBreaker(redis, str(account.id))
            try:
                async with cb.guard():
                    provider = ProviderFactory.create(
                        account.provider_type, account.credentials
                    )
                    docs = await provider.poll_incoming(account.tenant_id)

                for doc in docs:
                    existing = (
                        await session.execute(
                            select(IncomingDocumentModel).where(
                                IncomingDocumentModel.provider_document_id
                                == doc.provider_document_id,
                                IncomingDocumentModel.provider_account_id == account.id,
                            )
                        )
                    ).scalar_one_or_none()

                    if existing is None:
                        row = IncomingDocumentModel(
                            id=uuid.uuid4(),
                            tenant_id=account.tenant_id,
                            provider_account_id=account.id,
                            provider_document_id=doc.provider_document_id,
                            sender_inn=doc.sender_inn,
                            sender_name=doc.sender_name,
                            document_type=doc.document_type,
                            document_date=doc.document_date,
                            raw_payload=doc.raw_payload,
                            received_at=now,
                        )
                        session.add(row)
                        stats["new_docs"] += 1
                        INCOMING_DOCUMENTS_POLLED.labels(
                            provider=account.provider_type
                        ).inc()

                await cb.record_success()

            except Exception as exc:
                stats["errors"] += 1
                await cb.record_failure()
                log.warning(
                    "poll_incoming_error",
                    account_id=str(account.id),
                    error=str(exc),
                )

        await session.commit()

    return stats


@shared_task(
    name="edo.poll_incoming",
    queue="edo.sync",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def poll_incoming_task(self) -> None:  # type: ignore[override]
    stats = asyncio.get_event_loop().run_until_complete(_poll())
    log.info("poll_incoming_complete", **stats)
