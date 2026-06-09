from __future__ import annotations

from enum import StrEnum


class UnifiedDocumentStatus(StrEnum):

    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

    @property
    def is_terminal(self) -> bool:
        return self in {
            UnifiedDocumentStatus.SIGNED,
            UnifiedDocumentStatus.REJECTED,
            UnifiedDocumentStatus.CANCELLED,
            UnifiedDocumentStatus.FAILED,
        }

    @property
    def is_retryable(self) -> bool:
        return self in {
            UnifiedDocumentStatus.PENDING,
            UnifiedDocumentStatus.SENDING,
            UnifiedDocumentStatus.FAILED,
        }
