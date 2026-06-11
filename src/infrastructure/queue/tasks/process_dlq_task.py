from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from celery import shared_task
from sqlalchemy import select

from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.database.models import DLQEntryModel
from src.infrastructure.queue.tasks.send_document_task import send_document
from src.infrastructure.observability.metrics import DELIVERIES_IN_DLQ

log = structlog.get_logger(__name__)


async def _process_dlq() -> dict[str, int]:
    stats = {"scanned": 0, "replayed": 0, "skipped": 0}
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        stmt = select(DLQEntryModel).where(
            DLQEntryModel.replayed_at.is_(None),
            DLQEntryModel.retryable.is_(True),
        )
        entries = list((await session.execute(stmt)).scalars())
        stats["scanned"] = len(entries)

        DELIVERIES_IN_DLQ.set(len(entries))

        for entry in entries:
            try:
                send_document.apply_async(
                    kwargs={
                        "delivery_id": str(entry.delivery_id),
                        "file_bytes_hex": str(entry.payload.get("file_bytes_hex", "")),
                    },
                    queue="edo.send",
                )
                entry.replayed_at = now
                stats["replayed"] += 1
                log.info("dlq_auto_replayed", entry_id=str(entry.id))
            except Exception as exc:
                stats["skipped"] += 1
                log.warning("dlq_replay_error", entry_id=str(entry.id), error=str(exc))

        await session.commit()

    return stats


@shared_task(
    name="edo.process_dlq",
    queue="edo.dlq",
    bind=True,
    max_retries=0,
    ignore_result=True,
)
def process_dlq_task(self) -> None:  # type: ignore[override]
    stats = asyncio.get_event_loop().run_until_complete(_process_dlq())
    log.info("process_dlq_complete", **stats)
