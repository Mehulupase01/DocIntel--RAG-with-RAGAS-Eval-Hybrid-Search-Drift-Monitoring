"""API routers."""

from .answer import router as answer_router
from .documents import router as documents_router
from .eval import router as eval_router
from .health import router as health_router
from .search import router as search_router

__all__ = ["answer_router", "documents_router", "eval_router", "health_router", "search_router"]
