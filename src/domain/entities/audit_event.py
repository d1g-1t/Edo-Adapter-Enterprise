from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class AuditEvent:

    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_user_id: uuid.UUID | None
    resource_type: str
    resource_id: uuid.UUID
    event_type: str
    trace_id: str | None
    payload: dict[str, object]
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        tenant_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        event_type: str,
        payload: dict[str, object] | None = None,
        actor_user_id: uuid.UUID | None = None,
        trace_id: str | None = None,
    ) -> AuditEvent:
        return cls(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=event_type,
            trace_id=trace_id,
            payload=payload or {},
            created_at=datetime.now(UTC),
        )
