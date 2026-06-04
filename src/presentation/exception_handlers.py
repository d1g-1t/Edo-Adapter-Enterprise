from __future__ import annotations

from fastapi import Request, status
from fastapi.responses import ORJSONResponse

from src.domain.exceptions.domain_exceptions import (
    AuthenticationError,
    AuthorizationError,
    CircuitOpenError,
    DeliveryAlreadyFinalError,
    DLQEntryNotFoundError,
    DocumentNotFoundError,
    DomainError,
    DuplicateDocumentError,
    IdempotencyConflictError,
    ProviderAccountNotFoundError,
    ProviderPermanentError,
    ProviderTransientError,
    WebhookSignatureError,
)


def _error_response(status_code: int, code: str, message: str) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message}},
    )


async def domain_error_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_400_BAD_REQUEST, exc.code, exc.message)


async def not_found_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc.code, exc.message)


async def conflict_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc.code, exc.message)


async def unauthorized_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_401_UNAUTHORIZED, exc.code, exc.message)


async def forbidden_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_403_FORBIDDEN, exc.code, exc.message)


async def service_unavailable_handler(request: Request, exc: DomainError) -> ORJSONResponse:
    return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, exc.code, exc.message)


EXCEPTION_HANDLERS: list[tuple[type[Exception], object]] = [
    (DocumentNotFoundError, not_found_handler),
    (DeliveryAlreadyFinalError, conflict_handler),
    (DLQEntryNotFoundError, not_found_handler),
    (ProviderAccountNotFoundError, not_found_handler),
    (DuplicateDocumentError, conflict_handler),
    (IdempotencyConflictError, conflict_handler),
    (AuthenticationError, unauthorized_handler),
    (AuthorizationError, forbidden_handler),
    (CircuitOpenError, service_unavailable_handler),
    (ProviderTransientError, service_unavailable_handler),
    (ProviderPermanentError, domain_error_handler),
    (WebhookSignatureError, domain_error_handler),
    (DomainError, domain_error_handler),
]
