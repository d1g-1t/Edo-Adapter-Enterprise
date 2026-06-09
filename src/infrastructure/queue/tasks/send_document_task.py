from __future__ import annotations

import asyncio
import uuid
from typing import Any

from celery import Task

from src.core.logging import get_logger
from src.domain.entities.audit_event import AuditEvent
from src.domain.exceptions.domain_exceptions import (
    CircuitOpenError,
    ProviderPermanentError,
    ProviderTransientError,
)
from src.infrastructure.database.repositories import (
    SQLAuditRepository,
    SQLDeliveryRepository,
    SQLProviderAccountRepository,
)
from src.infrastructure.database.session import AsyncSessionFactory
from src.infrastructure.providers.provider_factory import ProviderFactory
from src.infrastructure.queue.celery_app import celery_app
from src.infrastructure.reliability.circuit_breaker import CircuitBreaker
from src.infrastructure.reliability.retry_backoff import (
    compute_next_retry,
    should_retry,
)
from src.infrastructure.cache.redis_client import get_redis

logger = get_logger(__name__)


@celery_app.task(
    name="src.infrastructure.queue.tasks.send_document_task.send_document",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def send_document(self: Task, delivery_id: str, file_bytes_hex: str) -> dict[str, Any]:
    return asyncio.get_event_loop().run_until_complete(
        _send_document_async(delivery_id, file_bytes_hex)
    )


async def _send_document_async(delivery_id: str, file_bytes_hex: str) -> dict[str, Any]:
    delivery_uuid = uuid.UUID(delivery_id)
    file_bytes = bytes.fromhex(file_bytes_hex)
    circuit = CircuitBreaker(get_redis())

    async with AsyncSessionFactory() as session:
        delivery_repo = SQLDeliveryRepository(session)
        account_repo = SQLProviderAccountRepository(session)
        audit_repo = SQLAuditRepository(session)

        delivery = await delivery_repo.get_by_id(delivery_uuid)
        if delivery is None:
            logger.error("send_document.delivery_not_found", delivery_id=delivery_id)
            return {"status": "not_found"}

        account = await account_repo.get_by_id(delivery.provider_account_id)
        if account is None or not account.is_active:
            delivery.mark_failed("PROVIDER_ACCOUNT_INACTIVE", "Provider account not active")
            await delivery_repo.update(delivery)
            await session.commit()
            return {"status": "failed"}

        try:
            await circuit.guard(str(account.id))
        except CircuitOpenError:
            delivery.mark_failed("CIRCUIT_OPEN", "Circuit breaker is OPEN")
            delivery.schedule_retry(compute_next_retry(delivery.retry_count))
            await delivery_repo.update(delivery)
            await session.commit()
            return {"status": "circuit_open"}

        delivery.mark_sending()
        await delivery_repo.update(delivery)
        await session.commit()

        provider = ProviderFactory.create(account.provider_type, account.credentials_json)

        try:
            result = await provider.send_document(
                sender_inn=str(delivery.document_id),
                sender_kpp=None,
                recipient_inn="0000000000",
                recipient_kpp=None,
                document_type="INVOICE",
                title="Document",
                file_name="document.bin",
                mime_type="application/octet-stream",
                file_bytes=file_bytes,
                metadata={},
            )
            delivery.mark_sent(result.provider_document_id)
            await circuit.record_success(str(account.id))

        except ProviderTransientError as exc:
            await circuit.record_failure(str(account.id))
            if should_retry(delivery.retry_count):
                delivery.schedule_retry(compute_next_retry(delivery.retry_count))
                logger.warning(
                    "send_document.transient_error.retry_scheduled",
                    delivery_id=delivery_id,
                    retry_count=delivery.retry_count,
                    error=str(exc),
                )
            else:
                delivery.mark_failed(exc.code, str(exc))
                _write_dlq(session, delivery, exc.code, str(exc), retryable=True)

        except ProviderPermanentError as exc:
            delivery.mark_failed(exc.code, str(exc))
            _write_dlq(session, delivery, exc.code, str(exc), retryable=False)
            logger.error("send_document.permanent_error", delivery_id=delivery_id, error=str(exc))

        except Exception as exc:
            delivery.mark_failed("UNKNOWN_ERROR", str(exc))
            _write_dlq(session, delivery, "UNKNOWN_ERROR", str(exc), retryable=False)
            logger.exception("send_document.unexpected_error", delivery_id=delivery_id)

        finally:
            audit = AuditEvent.create(
                tenant_id=delivery.tenant_id,
                resource_type="delivery",
                resource_id=delivery.id,
                event_type=f"delivery.status.{delivery.unified_status.value.lower()}",
                payload={"unified_status": delivery.unified_status.value},
            )
            await audit_repo.save(audit)
            await delivery_repo.update(delivery)
            await session.commit()

    return {"status": delivery.unified_status.value}


def _write_dlq(
    session: Any,
    delivery: Any,
    code: str,
    message: str,
    retryable: bool,
) -> None:
    from src.infrastructure.database.models import DLQEntryModel
    entry = DLQEntryModel(
        id=uuid.uuid4(),
        tenant_id=delivery.tenant_id,
        delivery_id=delivery.id,
        provider_account_id=delivery.provider_account_id,
        task_name="send_document",
        payload={"delivery_id": str(delivery.id)},
        reason_code=code,
        reason_message=message,
        retryable=retryable,
    )
    session.add(entry)
