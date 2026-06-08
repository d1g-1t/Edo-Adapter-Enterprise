from __future__ import annotations


class DomainError(Exception):

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class DocumentNotFoundError(DomainError):
    def __init__(self, document_id: object) -> None:
        super().__init__(f"Document not found: {document_id}", "DOCUMENT_NOT_FOUND")


class DuplicateDocumentError(DomainError):
    def __init__(self, internal_id: object) -> None:
        super().__init__(f"Document already exists: {internal_id}", "DUPLICATE_DOCUMENT")


class DeliveryNotFoundError(DomainError):
    def __init__(self, delivery_id: object) -> None:
        super().__init__(f"Delivery not found: {delivery_id}", "DELIVERY_NOT_FOUND")


class DeliveryAlreadyFinalError(DomainError):
    def __init__(self, delivery_id: object) -> None:
        super().__init__(f"Delivery is already final: {delivery_id}", "DELIVERY_ALREADY_FINAL")


class IdempotencyConflictError(DomainError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Idempotency key already exists: {key}", "IDEMPOTENCY_CONFLICT")


class ProviderAccountNotFoundError(DomainError):
    def __init__(self, account_id: object) -> None:
        super().__init__(f"Provider account not found: {account_id}", "PROVIDER_ACCOUNT_NOT_FOUND")


class ProviderAccountInactiveError(DomainError):
    def __init__(self, account_id: object) -> None:
        super().__init__(f"Provider account is inactive: {account_id}", "PROVIDER_ACCOUNT_INACTIVE")


class ProviderTransientError(DomainError):

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, "PROVIDER_TRANSIENT_ERROR")
        self.provider = provider


class ProviderPermanentError(DomainError):

    def __init__(self, message: str, provider: str) -> None:
        super().__init__(message, "PROVIDER_PERMANENT_ERROR")
        self.provider = provider


class ProviderRateLimitError(ProviderTransientError):

    def __init__(self, provider: str) -> None:
        super().__init__("Provider rate limit exceeded", provider)
        self.code = "PROVIDER_RATE_LIMIT"


class CircuitOpenError(DomainError):

    def __init__(self, provider_account_id: object) -> None:
        super().__init__(
            f"Circuit breaker OPEN for account: {provider_account_id}",
            "CIRCUIT_OPEN",
        )


class WebhookSignatureError(DomainError):
    def __init__(self, provider: str) -> None:
        super().__init__(f"Webhook signature invalid for provider: {provider}", "WEBHOOK_SIGNATURE_INVALID")


class WebhookDuplicateError(DomainError):
    def __init__(self, event_id: str) -> None:
        super().__init__(f"Duplicate webhook event: {event_id}", "WEBHOOK_DUPLICATE")


class AuthenticationError(DomainError):
    def __init__(self) -> None:
        super().__init__("Authentication failed", "AUTHENTICATION_FAILED")


class AuthorizationError(DomainError):
    def __init__(self, action: str) -> None:
        super().__init__(f"Not authorized to: {action}", "AUTHORIZATION_FAILED")


# ── DLQ ───────────────────────────────────────────────────────────────────

class DLQEntryNotFoundError(DomainError):
    def __init__(self, entry_id: object) -> None:
        super().__init__(f"DLQ entry not found: {entry_id}", "DLQ_ENTRY_NOT_FOUND")


class DLQEntryNotRetryableError(DomainError):
    def __init__(self, entry_id: object) -> None:
        super().__init__(f"DLQ entry is not retryable: {entry_id}", "DLQ_ENTRY_NOT_RETRYABLE")
