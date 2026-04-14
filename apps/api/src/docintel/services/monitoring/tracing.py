from __future__ import annotations

import time
import uuid

import structlog
from fastapi import Request

from .metrics import record_request


async def tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path, method=request.method)
    start = time.perf_counter()
    response = await call_next(request)
    duration_seconds = time.perf_counter() - start

    response.headers["X-Request-ID"] = request_id
    record_request(request.method, request.url.path, response.status_code, duration_seconds)
    structlog.get_logger(__name__).info(
        "docintel.request_complete",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=int(duration_seconds * 1000),
    )
    structlog.contextvars.clear_contextvars()
    return response
