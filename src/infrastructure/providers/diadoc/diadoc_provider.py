from __future__ import annotations

import time
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
_BASE_URL = "https://diadoc-api.kontur.ru"

_STATUS_MAP: dict[str, str] = {
    "UnknownStatus": "UNKNOWN",
    "Sent": "SENT",
    "Delivered": "DELIVERED",
    "Received": "DELIVERED",
    "SignatureRequestSent": "DELIVERED",
    "WaitingForSenderSignature": "DELIVERING",
    "FinishedWithOneSignedDocument": "SIGNED",
    "Signed": "SIGNED",
    "SignedAndInvoiceConfirmationSent": "SIGNED",
    "InvalidSignature": "REJECTED",
    "Rejected": "REJECTED",
}


class DiadocProvider(IEDOProvider):

    def __init__(self, credentials: dict[str, Any]) -> None:
        self._client_id: str = credentials["client_id"]
        self._login: str = credentials["login"]
        self._password: str = credentials["password"]
        self._box_id: str = credentials.get("box_id", "")
        self._token: str | None = None
        self._token_expires: float = 0.0
        settings = get_settings()
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(
                connect=settings.provider_connect_timeout_seconds,
                read=settings.provider_request_timeout_seconds,
                write=settings.provider_request_timeout_seconds,
                pool=5.0,
            ),
            http2=True,
        )

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires:
            return self._token

        response = await self._http.post(
            "/V2/Authenticate",
            params={"type": "password"},
            content=f"{self._login}:{self._password}".encode(),
            headers={"Content-Type": "application/octet-stream"},
        )
        self._handle_errors(response, "auth")
        self._token = response.text
        self._token_expires = time.time() + 3600
        return self._token

    def _handle_errors(self, response: httpx.Response, context: str) -> None:
        if response.status_code == 429:
            raise ProviderRateLimitError(provider="DIADOC")
        if response.status_code >= 500:
            raise ProviderTransientError(
                f"Diadoc server error [{response.status_code}] on {context}",
                provider="DIADOC",
            )
        if response.status_code >= 400:
            raise ProviderPermanentError(
                f"Diadoc client error [{response.status_code}] on {context}: {response.text}",
                provider="DIADOC",
            )

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
        token = await self._ensure_token()
        response = await self._http.post(
            "/V3/PostMessage",
            headers={"Authorization": f"DiadocAuth ddauth_api_client_id={self._client_id},ddauth_token={token}"},
            json={
                "FromBoxId": self._box_id,
                "ToBoxId": recipient_inn,
                "DocumentAttachments": [
                    {
                        "TypeNamedId": document_type.lower(),
                        "FileName": file_name,
                        "SignedContent": {"Content": file_bytes.hex()},
                    }
                ],
            },
        )
        self._handle_errors(response, "send")
        data: dict[str, Any] = response.json()
        provider_doc_id: str = data.get("MessageId", "")
        logger.info("diadoc.send.success", message_id=provider_doc_id)
        return SendResult(provider_document_id=provider_doc_id, raw_status="Sent")

    async def get_document_status(self, provider_document_id: str) -> StatusResult:
        token = await self._ensure_token()
        response = await self._http.get(
            f"/V3/GetMessage",
            params={"boxId": self._box_id, "messageId": provider_document_id},
            headers={"Authorization": f"DiadocAuth ddauth_api_client_id={self._client_id},ddauth_token={token}"},
        )
        self._handle_errors(response, "status")
        data = response.json()
        raw_status: str = data.get("MessageType", "UnknownStatus")
        unified = _STATUS_MAP.get(raw_status, "UNKNOWN")
        return StatusResult(
            provider_document_id=provider_document_id,
            unified_status=unified,
            raw_status=raw_status,
            extra=data,
        )

    async def poll_incoming(
        self,
        *,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[IncomingDocumentData]:
        return []

    async def validate_webhook(self, payload: bytes, headers: dict[str, str]) -> bool:
        sig = headers.get("x-kontur-signature", "")
        if not sig:
            return True
        return True

    async def parse_webhook(self, payload: dict[str, Any]) -> WebhookParseResult:
        return WebhookParseResult(
            external_event_id=payload.get("MessageId"),
            provider_document_id=payload.get("MessageId"),
            unified_status=_STATUS_MAP.get(str(payload.get("MessageType", "")), "UNKNOWN"),
            raw_payload=payload,
        )

    async def health_check(self) -> tuple[bool, int]:
        import time as _time
        start = _time.monotonic()
        try:
            response = await self._http.get("/V2/GetOrganizationsByInnKpp", params={"inn": "0000000000"})
            ms = int((_time.monotonic() - start) * 1000)
            return response.status_code < 500, ms
        except Exception:
            return False, 0
