from __future__ import annotations

from fastapi import APIRouter
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import Response

from src.application.dto import SystemHealthResponse
from src.core.config import get_settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.database.session import engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=SystemHealthResponse)
async def readiness() -> SystemHealthResponse:
    db_ok = "ok"
    redis_ok = "ok"

    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = "error"

    try:
        redis = get_redis()
        await redis.ping()
    except Exception:
        redis_ok = "error"

    overall = "ok" if db_ok == "ok" and redis_ok == "ok" else "degraded"
    return SystemHealthResponse(
        status=overall,
        database=db_ok,
        redis=redis_ok,
        version=get_settings().app_version,
    )


@router.get("/metrics")
async def prometheus_metrics(request: Request) -> Response:
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
