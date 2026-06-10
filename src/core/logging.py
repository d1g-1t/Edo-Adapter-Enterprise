from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict

from src.core.config import get_settings


def _mask_sensitive(_: Any, __: str, event_dict: EventDict) -> EventDict:
    sensitive = {"password", "token", "secret", "credential", "authorization", "hashed_password"}
    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive):
            event_dict[key] = "***MASKED***"
    return event_dict


def configure_logging() -> None:
    settings = get_settings()

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.enable_log_masking:
        shared_processors.append(_mask_sensitive)

    if settings.app_env == "prod":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            *shared_processors,
            renderer,
        ]
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    log_level = logging.DEBUG if settings.debug else logging.INFO
    root_logger.setLevel(log_level)

    for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "celery"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
