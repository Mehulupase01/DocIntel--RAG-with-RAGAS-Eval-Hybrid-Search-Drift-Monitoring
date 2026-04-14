"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_setup import configure_logging, get_logger
from .routers.documents import router as documents_router
from .routers.health import router as health_router
from .routers.metrics import metrics_app
from .routers.search import router as search_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger.info("docintel.startup")
    yield
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.mount("/metrics", metrics_app)

    return app


app = create_app()
