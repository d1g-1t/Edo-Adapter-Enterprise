from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from src.application.interfaces.i_edo_provider import (
    IEDOProvider,
    IncomingDocumentData,
    SendResult,
    StatusResult,
    WebhookParseResult,
)
from src.core.config import get_settings
from src.core.logging import get_logger
from src.domain.exceptions.domain_exceptions import (
    ProviderPermanentError,
    ProviderRateLimitError,
    ProviderTransientError,
)

logger = get_logger(__name__)
_BASE_URL = "https://edo.kontur.ru/api"

_STATUS_MAP: dict[str, str] = {
    "sent": "SENT",
    "delivered": "DELIVERED",
    "signed": "SIGNED",
    "rejected": "REJECTED",
    "cancelled": "CANCELLED",
}


class KonturEDOProvider(IEDOProvider):

    def __init__(self, credentials: dict[str, Any]) -> None:
        self._api_key: str = credentials["api_key"]
        self._box_id: str = credentials["box_id"]
        settings = get_settings()
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=httpx.Timeout(
                connect=settings.provider_connect_timeout_seconds,
                read=settings.provider_request_timeout_seconds,
                write=settings.provider_request_timeout_seconds,
                pool=5.0,
            ),
            http2=True,
        )

    def _handle_errors(self, response: httpx.Response, context: str) -> None:
        if response.status_code == 429:
            raise ProviderRateLimitError(provider="KONTUR_EDO")
        if response.status_code >= 500:
            raise ProviderTransientError(
                f"Kontur EDO error [{response.status_code}] on {context}", provider="KONTUR_EDO"
            )
        if response.status_code >= 400:
            raise ProviderPermanentError(
                f"Kontur EDO client error [{response.status_code}]: {response.text}",
                provider="KONTUR_EDO",
            )

    async def send_document(self, *, sender_inn: str, sender_kpp: str | None,
                            recipient_inn: str, recipient_kpp: str | None,
                            document_type: str, title: str, file_name: str,
                            mime_type: str, file_bytes: bytes, metadata: dict[str, Any]) -> SendResult:
        response = await self._http.post(
            "/v1/documents",
            json={
                "boxId": self._box_id,
                "recipientInn": recipient_inn,
                "recipientKpp": recipient_kpp,
                "documentType": document_type,
                "title": title,
                "fileName": file_name,
            },
        )
        self._handle_errors(response, "send")
        doc_id: str = response.json().get("documentId", "")
        return SendResult(provider_document_id=doc_id, raw_status="sent")

    async def get_document_status(self, provider_document_id: str) -> StatusResult:
        response = await self._http.get(f"/v1/documents/{provider_document_id}")
        self._handle_errors(response, "status")
        raw: str = response.json().get("status", "")
        return StatusResult(
            provider_document_id=provider_document_id,
            unified_status=_STATUS_MAP.get(raw.lower(), "UNKNOWN"),
            raw_status=raw,
            extra={},
        )

    async def poll_incoming(self, *, since: datetime | None = None, limit: int = 100) -> list[IncomingDocumentData]:
        params: dict[str, Any] = {"boxId": self._box_id, "limit": limit}
        if since:
            params["since"] = since.isoformat()
        response = await self._http.get("/v1/incoming", params=params)
        self._handle_errors(response, "poll")
        items: list[dict[str, Any]] = response.json().get("items", [])
        return [
            IncomingDocumentData(
                provider_document_id=item["documentId"],
                document_type=item.get("documentType", "UNKNOWN"),
                sender_inn=item.get("senderInn", ""),
                sender_name=item.get("senderName"),
                file_name=item.get("fileName", ""),
                mime_type=item.get("mimeType", "application/octet-stream"),
                unified_status=_STATUS_MAP.get(item.get("status", "").lower(), "UNKNOWN"),
                metadata=item.get("metadata", {}),
                received_at=datetime.fromisoformat(item["receivedAt"]),
            )
            for item in items
        ]

    async def validate_webhook(self, payload: bytes, headers: dict[str, str]) -> bool:
        return True

    async def parse_webhook(self, payload: dict[str, Any]) -> WebhookParseResult:
        return WebhookParseResult(
            external_event_id=payload.get("eventId"),
            provider_document_id=payload.get("documentId"),
            unified_status=_STATUS_MAP.get(str(payload.get("status", "")).lower(), "UNKNOWN"),
            raw_payload=payload,
        )

    async def health_check(self) -> tuple[bool, int]:
        import time as _time
        start = _time.monotonic()
        try:
            r = await self._http.get("/v1/ping")
            ms = int((_time.monotonic() - start) * 1000)
            return r.status_code < 500, ms
        except Exception:
            return False, 0
