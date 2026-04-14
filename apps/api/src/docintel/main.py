"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_setup import configure_logging, get_logger
from .routers.answer import router as answer_router
from .routers.documents import router as documents_router
from .routers.drift import router as drift_router
from .routers.eval import router as eval_router
from .routers.health import router as health_router
from .routers.metrics import router as metrics_router
from .routers.search import router as search_router
from .services.drift.scheduler import start_drift_scheduler, stop_drift_scheduler
from .services.monitoring.langsmith_setup import configure_langsmith
from .services.monitoring.tracing import tracing_middleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    langsmith_enabled = configure_langsmith()
    scheduler = start_drift_scheduler()
    logger.info("docintel.startup")
    logger.info("docintel.langsmith", enabled=langsmith_enabled)
    logger.info("docintel.scheduler_jobs", jobs=[job.id for job in scheduler.get_jobs()])
    yield
    stop_drift_scheduler()
    logger.info("docintel.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="DocIntel API",
        version="0.1.0",
        lifespan=lifespan,
    )

    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(documents_router)
    api_router.include_router(health_router)
    api_router.include_router(search_router)
    api_router.include_router(answer_router)
    api_router.include_router(eval_router)
    api_router.include_router(drift_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(tracing_middleware)
    app.include_router(api_router)
    app.include_router(metrics_router)

    return app


app = create_app()
