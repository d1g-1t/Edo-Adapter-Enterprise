from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

from src.infrastructure.cache.redis_client import get_redis

log = structlog.get_logger(__name__)

_IDEMPOTENCY_PREFIX = "idempotency:"


async def _cleanup() -> dict[str, int]:
    stats = {"scanned": 0, "deleted": 0}
    redis = await get_redis()

    cursor = 0
    while True:
        cursor, keys = await redis.scan(
            cursor=cursor, match=f"{_IDEMPOTENCY_PREFIX}*", count=100
        )
        stats["scanned"] += len(keys)
        if cursor == 0:
            break

    log.info("idempotency_cleanup_complete", **stats)
    return stats


@shared_task(
    name="edo.cleanup_idempotency",
    queue="edo.health",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def cleanup_idempotency_task(self) -> None:
    asyncio.get_event_loop().run_until_complete(_cleanup())
