from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

DOCUMENT_SEND_TOTAL = Counter(
    "edo_document_send_total",
    "Total document send attempts",
    labelnames=["provider_type", "status"],
)

DOCUMENT_SEND_DURATION_SECONDS = Histogram(
    "edo_document_send_duration_seconds",
    "Time spent sending a document to the provider",
    labelnames=["provider_type"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

DELIVERY_STATUS_TRANSITIONS = Counter(
    "edo_delivery_status_transitions_total",
    "Number of delivery status transitions",
    labelnames=["from_status", "to_status", "provider_type"],
)

DELIVERY_RETRIES = Counter(
    "edo_delivery_retries_total",
    "Number of delivery retry attempts",
    labelnames=["provider_type"],
)

DELIVERIES_IN_DLQ = Gauge(
    "edo_deliveries_in_dlq",
    "Current number of entries in the DLQ",
    labelnames=["tenant_id"],
)

PROVIDER_HEALTH_STATUS = Gauge(
    "edo_provider_health_status",
    "Provider account health (1=healthy, 0=unhealthy)",
    labelnames=["provider_account_id", "provider_type"],
)

PROVIDER_RESPONSE_TIME_MS = Histogram(
    "edo_provider_response_time_ms",
    "Provider HTTP response time in milliseconds",
    labelnames=["provider_type"],
    buckets=[10, 50, 100, 250, 500, 1000, 2500, 5000],
)

CIRCUIT_BREAKER_STATE = Gauge(
    "edo_circuit_breaker_state",
    "Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    labelnames=["provider_account_id"],
)

WEBHOOK_RECEIVED_TOTAL = Counter(
    "edo_webhook_received_total",
    "Total webhooks received",
    labelnames=["provider_type", "signature_status"],
)

WEBHOOK_PROCESSING_ERRORS = Counter(
    "edo_webhook_processing_errors_total",
    "Webhook processing errors",
    labelnames=["provider_type"],
)

INCOMING_DOCUMENTS_POLLED = Counter(
    "edo_incoming_documents_polled_total",
    "Total incoming documents discovered via polling",
    labelnames=["provider_type"],
)
