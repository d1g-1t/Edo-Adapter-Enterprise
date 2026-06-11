# EDO-Adapter Enterprise

Enterprise integration layer for Russian EDO/KEDO providers (Diadoc, SBIS, Kontur EDO).
Unified API, provider strategy abstraction, reliability patterns, and observability-first ops.

Not a thin wrapper. Not a CRUD API. An actual **enterprise document exchange platform**.

---

## What this is

A backend service that sits between your internal systems and Russian EDO providers,
giving you a clean unified interface regardless of which provider you're talking to.
Send a document once — the adapter handles routing, retries, circuit breaking, dead-letter
queuing, webhook validation, status normalisation, and audit trail.

Built to demonstrate senior-level Python/FastAPI engineering for the Russian LegalTech market.

---

## Architecture

```
┌──────────────┐     HTTP/REST      ┌─────────────────────────────────────────┐
│  Client Apps │ ─────────────────► │  FastAPI (Presentation Layer)           │
└──────────────┘                    │  - PASETO auth, rate-limiting, CORS     │
                                    │  - Request ID, security headers          │
                                    └──────────────┬──────────────────────────┘
                                                   │
                                    ┌──────────────▼──────────────────────────┐
                                    │  Application Layer (CQRS use-cases)     │
                                    │  - Commands, Queries, DTOs               │
                                    └──────────────┬──────────────────────────┘
                                                   │
                                    ┌──────────────▼──────────────────────────┐
                                    │  Domain Layer (DDD + Clean Architecture) │
                                    │  - Entities, Value Objects, Exceptions   │
                                    │  - Repository interfaces (ports)         │
                                    └──────────────┬──────────────────────────┘
                                                   │
                        ┌──────────────────────────▼──────────────────────────┐
                        │  Infrastructure (Adapters)                           │
                        │  ┌──────────┐  ┌────────┐  ┌────────┐  ┌────────┐  │
                        │  │  Diadoc  │  │  SBIS  │  │ Kontur │  │  Stub  │  │
                        │  └──────────┘  └────────┘  └────────┘  └────────┘  │
                        │  SQLAlchemy 2 async │ Redis │ Celery │ OTel         │
                        └─────────────────────────────────────────────────────┘
```

**Patterns used**: Clean Architecture, DDD, Hexagonal (Ports & Adapters), CQRS,
Circuit Breaker, Exponential Backoff + Jitter, Dead Letter Queue, Outbox, Idempotency.

---

## Tech stack

| Layer | Tech |
|-------|------|
| API Framework | FastAPI 0.115 + Uvicorn |
| Auth | PASETO v4 local (not JWT) |
| ORM | SQLAlchemy 2 async + asyncpg |
| Migrations | Alembic (async) |
| Cache / Broker | Redis 7 |
| Task queue | Celery 5 + Beat |
| HTTP client | HTTPX (HTTP/2) |
| Validation | Pydantic v2 |
| DI | dependency-injector |
| Logging | structlog + JSON |
| Tracing | OpenTelemetry → Tempo |
| Metrics | Prometheus + Grafana |
| Tests | pytest-asyncio + respx + HTTPX |

---

## Ports (non-standard to avoid conflicts)

| Service | Port |
|---------|------|
| API | **8099** |
| PostgreSQL | **5499** |
| Redis | **6399** |
| Flower | **5599** |
| Prometheus | **9099** |
| Grafana | **3099** |
| Tempo gRPC | **4399** |
| Loki | **3199** |

---

## Quickstart

```bash
# Clone & enter
git clone <repo> && cd edo-adapter-enterprise

# Full setup from scratch — creates venv, runs migrations, seeds demo users
make setup

# Start the full Docker stack (api + worker + all infra)
make up

# Docs
open http://localhost:8099/api/docs
```

### Demo credentials (seeded by `make setup`)

```
admin@demo.corp  / admin1234!   → role: admin
viewer@demo.corp / viewer1234!  → role: viewer
```

---

## Common commands

```bash
make setup        # full bootstrap after clone
make up           # start docker stack
make down         # stop docker stack
make test         # run all tests with coverage
make test-unit    # unit tests only (no infra required)
make lint         # ruff + mypy
make format       # ruff format + autofix
make migrate      # alembic upgrade head
make seed         # re-seed demo data
make dev          # run API locally (hot reload)
make dev-worker   # run Celery worker locally
make logs         # tail api + worker logs
make clean        # nuke everything (venv, volumes)
```

---

## API overview

```
POST   /api/v1/auth/login                   # get PASETO tokens
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me

POST   /api/v1/provider-accounts/          # register Diadoc / SBIS / Kontur / Stub
GET    /api/v1/provider-accounts/
POST   /api/v1/provider-accounts/{id}/activate
POST   /api/v1/provider-accounts/{id}/deactivate

POST   /api/v1/documents/send              # send document (async, returns 202)
GET    /api/v1/documents/
GET    /api/v1/documents/{id}
GET    /api/v1/documents/{id}/deliveries   # all provider delivery attempts
GET    /api/v1/documents/{id}/status       # aggregated unified status
POST   /api/v1/documents/{id}/retry

GET    /api/v1/dlq/                        # dead-letter queue dashboard
POST   /api/v1/dlq/{id}/replay             # replay single entry
POST   /api/v1/dlq/replay-batch            # batch replay

GET    /api/v1/health/live                 # liveness probe
GET    /api/v1/health/ready                # readiness probe (DB + Redis check)
GET    /api/v1/health/metrics              # Prometheus metrics
```

---

## Key engineering decisions

**PASETO over JWT** — no algorithm confusion attacks, simpler key management.

**SQLAlchemy 2 async** — all I/O is non-blocking. `lazy="noload"` on relationships +
explicit `selectinload` where needed means zero N+1 queries by design.

**Per-provider circuit breaker in Redis** — shared state across API + worker processes.
Open → Half-Open → Closed transitions with configurable thresholds.

**Full jitter exponential backoff** — AWS-style. Avoids thundering herd on provider outages.

**Stub provider** — fully functional in-process provider. Local dev and all tests run
without any external EDO integration.

**Idempotent sends** — `(document_id, provider_account_id)` pair ensures duplicate requests
produce the same result without double-sending.

**UTC everywhere** — all datetimes are timezone-aware UTC. No naive datetimes in the codebase.

---

## Running tests

```bash
make test              # all tests + coverage report
make test-unit         # fast unit tests (no DB, no Redis)
make test-integration  # provider adapter tests
make test-e2e          # full API tests with in-memory SQLite
```

Coverage target: 80%+. The test suite covers value objects, domain entities,
retry logic, stub provider behaviour, and all API endpoints.

---

## Observability

| Tool | URL | What it shows |
|------|-----|---------------|
| Grafana | http://localhost:3099 | Dashboards (login: admin/admin) |
| Prometheus | http://localhost:9099 | Raw metrics |
| Flower | http://localhost:5599 | Celery task queue |

Metrics tracked: document send latency, delivery status transitions, DLQ size,
provider health, circuit breaker state, webhook receive rate.

---

## Project structure

```
src/
├── domain/          # Pure Python — no framework deps
│   ├── entities/    # EdoDocument, DocumentDelivery, ProviderAccount …
│   ├── value_objects/  # INN, UnifiedDocumentStatus, ProviderType …
│   ├── repositories/   # Abstract interfaces (ports)
│   └── exceptions/     # Domain exception hierarchy
├── application/     # Use cases, DTOs, provider interface
├── infrastructure/  # Adapters: DB, Redis, Celery, Providers, Observability
│   ├── database/    # SQLAlchemy models, repositories, Alembic migrations
│   ├── providers/   # Diadoc, SBIS, Kontur EDO, Stub
│   ├── queue/       # Celery app + tasks
│   ├── reliability/ # CircuitBreaker, RetryBackoff
│   └── observability/ # Prometheus metrics, OTel
├── presentation/    # FastAPI routers, middleware, exception handlers
└── core/            # Config (pydantic-settings), logging, telemetry, security
```

---

## Extending with a new provider

1. Implement `IEDOProvider` in `src/infrastructure/providers/your_provider/`
2. Add `YOUR_PROVIDER` to `ProviderType` enum
3. Register in `ProviderFactory.create()`
4. Done — routing, retry, circuit breaker, audit work automatically

---

## Related projects

This adapter connects naturally with:
- **LegalOpsAI-Pipeline** — AI-assisted document analysis
- **ContractForge** — contract lifecycle management
- **SecureDocVault** — encrypted document archive

Together they form a full in-house legal department backend stack for the Russian market.

---

MIT License · Built with FastAPI, SQLAlchemy 2, Celery, Redis, OpenTelemetry
