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
_BASE_URL = "https://online.sbis.ru"

_STATUS_MAP: dict[str, str] = {
    "Отправлен": "SENT",
    "Прочитан": "DELIVERED",
    "Подписан": "SIGNED",
    "Отклонён": "REJECTED",
    "Отозван": "CANCELLED",
}


class SBISProvider(IEDOProvider):

    def __init__(self, credentials: dict[str, Any]) -> None:
        self._login: str = credentials["login"]
        self._password: str = credentials["password"]
        self._reg_id: str = credentials.get("reg_id", "")
        self._sid: str | None = None
        settings = get_settings()
        self._http = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(
                connect=settings.provider_connect_timeout_seconds,
                read=settings.provider_request_timeout_seconds,
                write=settings.provider_request_timeout_seconds,
                pool=5.0,
            ),
        )

    async def _ensure_session(self) -> str:
        if self._sid:
            return self._sid
        response = await self._http.post(
            "/auth/service/",
            json={"jsonrpc": "2.0", "method": "СБИС.Аутентифицировать",
                  "params": {"Параметры": {"Логин": self._login, "Пароль": self._password}},
                  "id": 1},
        )
        self._handle_errors(response, "auth")
        self._sid = response.json()["result"]
        return self._sid

    def _handle_errors(self, response: httpx.Response, context: str) -> None:
        if response.status_code == 429:
            raise ProviderRateLimitError(provider="SBIS")
        if response.status_code >= 500:
            raise ProviderTransientError(f"SBIS error [{response.status_code}] on {context}", provider="SBIS")
        if response.status_code >= 400:
            raise ProviderPermanentError(f"SBIS client error [{response.status_code}]: {response.text}", provider="SBIS")
        if data := response.json():
            if "error" in data:
                raise ProviderPermanentError(str(data["error"]), provider="SBIS")

    async def send_document(self, *, sender_inn: str, sender_kpp: str | None, recipient_inn: str,
                            recipient_kpp: str | None, document_type: str, title: str,
                            file_name: str, mime_type: str, file_bytes: bytes,
                            metadata: dict[str, Any]) -> SendResult:
        sid = await self._ensure_session()
        response = await self._http.post(
            "/service/",
            headers={"X-SBISSessionID": sid},
            json={
                "jsonrpc": "2.0", "method": "СБИС.ЗаписатьДокумент",
                "params": {"Документ": {"НашОрг": {"РегНомер": self._reg_id},
                                         "Тип": document_type, "Название": title,
                                         "ИдФайла": file_name}},
                "id": 2,
            },
        )
        self._handle_errors(response, "send")
        doc_id: str = str(response.json().get("result", {}).get("Ид", ""))
        return SendResult(provider_document_id=doc_id, raw_status="Отправлен")

    async def get_document_status(self, provider_document_id: str) -> StatusResult:
        sid = await self._ensure_session()
        response = await self._http.post(
            "/service/",
            headers={"X-SBISSessionID": sid},
            json={"jsonrpc": "2.0", "method": "СБИС.ПрочитатьДокумент",
                  "params": {"Документ": {"Ид": provider_document_id}}, "id": 3},
        )
        self._handle_errors(response, "status")
        raw: str = str(response.json().get("result", {}).get("Состояние", ""))
        return StatusResult(
            provider_document_id=provider_document_id,
            unified_status=_STATUS_MAP.get(raw, "UNKNOWN"),
            raw_status=raw,
            extra={},
        )

    async def poll_incoming(self, *, since: datetime | None = None, limit: int = 100) -> list[IncomingDocumentData]:
        return []

    async def validate_webhook(self, payload: bytes, headers: dict[str, str]) -> bool:
        return True

    async def parse_webhook(self, payload: dict[str, Any]) -> WebhookParseResult:
        return WebhookParseResult(
            external_event_id=payload.get("Ид"),
            provider_document_id=payload.get("ИдДокумент"),
            unified_status=_STATUS_MAP.get(str(payload.get("Состояние", "")), "UNKNOWN"),
            raw_payload=payload,
        )

    async def health_check(self) -> tuple[bool, int]:
        import time as _time
        start = _time.monotonic()
        try:
            r = await self._http.get("/")
            ms = int((_time.monotonic() - start) * 1000)
            return r.status_code < 500, ms
        except Exception:
            return False, 0
