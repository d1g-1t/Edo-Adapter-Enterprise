from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.core.telemetry import configure_telemetry, instrument_fastapi
from src.presentation.api.v1 import (
    audit,
    auth,
    dlq,
    documents,
    health,
    incoming,
    provider_accounts,
    providers,
    webhooks,
)
from src.presentation.exception_handlers import EXCEPTION_HANDLERS
from src.presentation.middleware.request_id import RequestIDMiddleware
from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging()
    configure_telemetry()
    logger.info("edo_adapter.startup", version=get_settings().app_version)
    yield
    from src.infrastructure.cache.redis_client import close_redis
    from src.infrastructure.database.session import engine
    await close_redis()
    await engine.dispose()
    logger.info("edo_adapter.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_title,
        version=settings.app_version,
        docs_url="/api/docs" if settings.app_env != "prod" else None,
        redoc_url="/api/redoc" if settings.app_env != "prod" else None,
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestIDMiddleware)

    Instrumentator(excluded_handlers=["/api/v1/health/metrics"]).instrument(app).expose(
        app,
        endpoint="/api/v1/health/metrics",
        include_in_schema=False,
    )

    for exc_type, handler in EXCEPTION_HANDLERS:
        app.add_exception_handler(exc_type, handler)

    api_prefix = "/api/v1"
    app.include_router(auth.router, prefix=api_prefix)
    app.include_router(provider_accounts.router, prefix=api_prefix)
    app.include_router(documents.router, prefix=api_prefix)
    app.include_router(dlq.router, prefix=api_prefix)
    app.include_router(health.router, prefix=api_prefix)
    app.include_router(webhooks.router, prefix=api_prefix)
    app.include_router(incoming.router, prefix=api_prefix)
    app.include_router(audit.router, prefix=api_prefix)
    app.include_router(providers.router, prefix=api_prefix)

    instrument_fastapi(app)

    return app


app = create_app()
