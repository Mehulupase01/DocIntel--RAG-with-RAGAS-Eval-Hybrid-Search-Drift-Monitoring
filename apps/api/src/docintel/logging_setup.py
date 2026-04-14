"""Logging setup for DocIntel."""

from __future__ import annotations

import logging
from typing import Any

import structlog
from pydantic import ValidationError

from .config import Settings, get_settings


def _resolve_settings() -> Settings | None:
    try:
        return get_settings()
    except ValidationError:
        return None


def configure_logging(settings: Settings | None = None) -> None:
    resolved_settings = settings or _resolve_settings()
    log_level_name = (resolved_settings.log_level if resolved_settings else "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)
    renderer: structlog.types.Processor
    if resolved_settings and resolved_settings.log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    logging.basicConfig(level=log_level, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(*args: Any, **kwargs: Any) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(*args, **kwargs)

