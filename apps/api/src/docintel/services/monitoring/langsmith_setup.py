from __future__ import annotations

import os

from docintel.config import get_settings


def configure_langsmith() -> bool:
    settings = get_settings()
    if not settings.langsmith_api_key or not settings.langsmith_tracing:
        return False

    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project
    return True
