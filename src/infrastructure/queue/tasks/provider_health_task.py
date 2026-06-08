from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select

from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.database.models import (
    ProviderAccountModel,
    ProviderHealthSnapshotModel,
)
from src.infrastructure.providers.provider_factory import ProviderFactory
from src.infrastructure.observability.metrics import (
    PROVIDER_HEALTH_STATUS,
    PROVIDER_RESPONSE_TIME_MS,
    CIRCUIT_BREAKER_STATE,
)
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.reliability.circuit_breaker import CircuitBreaker

log = structlog.get_logger(__name__)


async def _check_health() -> dict[str, int]:
    stats = {"accounts": 0, "healthy": 0, "unhealthy": 0}
    redis = await get_redis()
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        accounts = list(
            (
                await session.execute(
                    select(ProviderAccountModel).where(
                        ProviderAccountModel.is_active.is_(True)
                    )
                )
            ).scalars()
        )
        stats["accounts"] = len(accounts)

        for account in accounts:
            cb = CircuitBreaker(redis, str(account.id))
            cb_state = await cb.get_state()

            CIRCUIT_BREAKER_STATE.labels(
                provider=account.provider_type,
                account_id=str(account.id),
            ).set({"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}.get(cb_state, -1))

            import time

            start_ms = time.monotonic() * 1000
            is_healthy = False
            error_detail: str | None = None

            try:
                provider = ProviderFactory.create(
                    account.provider_type, account.credentials
                )
                result = await provider.health_check()
                is_healthy = result.is_healthy
                error_detail = result.detail if not is_healthy else None
                stats["healthy" if is_healthy else "unhealthy"] += 1
            except Exception as exc:
                is_healthy = False
                error_detail = str(exc)
                stats["unhealthy"] += 1
                log.warning(
                    "health_check_error",
                    account_id=str(account.id),
                    provider=account.provider_type,
                    error=str(exc),
                )

            elapsed_ms = (time.monotonic() * 1000) - start_ms

            PROVIDER_HEALTH_STATUS.labels(
                provider=account.provider_type,
                account_id=str(account.id),
            ).set(1 if is_healthy else 0)

            PROVIDER_RESPONSE_TIME_MS.labels(
                provider=account.provider_type,
                account_id=str(account.id),
            ).observe(elapsed_ms)

            snapshot = ProviderHealthSnapshotModel(
                id=uuid.uuid4(),
                provider_account_id=account.id,
                is_healthy=is_healthy,
                response_time_ms=int(elapsed_ms),
                circuit_state=cb_state,
                error_detail=error_detail,
                checked_at=now,
            )
            session.add(snapshot)

        await session.commit()

    return stats


@shared_task(
    name="edo.provider_health",
    queue="edo.health",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def provider_health_task(self) -> None:
    stats = asyncio.get_event_loop().run_until_complete(_check_health())
    log.info("provider_health_complete", **stats)
