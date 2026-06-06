from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class SendResult:

    provider_document_id: str
    raw_status: str


@dataclass
class StatusResult:

    provider_document_id: str
    unified_status: str
    raw_status: str
    extra: dict[str, Any]


@dataclass
class IncomingDocumentData:

    provider_document_id: str
    document_type: str
    sender_inn: str
    sender_name: str | None
    file_name: str
    mime_type: str
    unified_status: str
    metadata: dict[str, Any]
    received_at: datetime


@dataclass
class WebhookParseResult:

    external_event_id: str | None
    provider_document_id: str | None
    unified_status: str | None
    raw_payload: dict[str, Any]


class IEDOProvider(ABC):

    @abstractmethod
    async def send_document(
        self,
        *,
        sender_inn: str,
        sender_kpp: str | None,
        recipient_inn: str,
        recipient_kpp: str | None,
        document_type: str,
        title: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
        metadata: dict[str, Any],
    ) -> SendResult:

    @abstractmethod
    async def get_document_status(self, provider_document_id: str) -> StatusResult:

    @abstractmethod
    async def poll_incoming(
        self,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[IncomingDocumentData]:

    @abstractmethod
    async def validate_webhook(
        self, payload: bytes, headers: dict[str, str]
    ) -> bool:

    @abstractmethod
    async def parse_webhook(
        self, payload: dict[str, Any]
    ) -> WebhookParseResult:

    @abstractmethod
    async def health_check(self) -> tuple[bool, int]:
