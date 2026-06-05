from __future__ import annotations

from enum import StrEnum


class DeliveryStatus(StrEnum):

    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    RETRYING = "RETRYING"
    DEAD = "DEAD"


class CircuitState(StrEnum):

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class WebhookSignatureStatus(StrEnum):

    VALID = "VALID"
    INVALID = "INVALID"
    SKIPPED = "SKIPPED"


class RetryState(StrEnum):

    PENDING = "PENDING"
    RETRYING = "RETRYING"
    EXHAUSTED = "EXHAUSTED"
    REPLAYED = "REPLAYED"
