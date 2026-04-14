"""Application settings for DocIntel."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    api_port: int = 8000
    debug: bool = False
    log_level: str = "INFO"
    log_format: str = "json"
    api_keys: list[str] = Field(default_factory=list)
    secret_key: str = "dev-secret-not-for-production"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_model_revision: str | None = None
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_model_revision: str | None = None
    model_cache_dir: str = "/app/.model_cache"

    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    default_generation_model: str = "minimax/minimax-m2.5:free"
    default_judge_model: str = "nvidia/nemotron-3-super-120b-a12b:free"

    langsmith_api_key: str | None = None
    langsmith_project: str = "docintel-dev"
    langsmith_tracing: bool = False

    artifact_storage_path: str = "/app/artifacts"

    max_upload_bytes: int = 52_428_800
    chunk_target_tokens: int = 512
    chunk_overlap_tokens: int = 64
    eu_ai_act_pdf_url: str | None = None

    default_top_k: int = 10
    default_rerank_top_n: int = 50
    default_rrf_k: int = 60

    eval_faithfulness_threshold: float = 0.85
    eval_context_precision_threshold: float = 0.88
    eval_context_recall_threshold: float = 0.80
    eval_answer_relevancy_threshold: float = 0.85

    drift_window_days: int = 7
    drift_reference_window_days: int = 7
    drift_warning_threshold: float = 0.15
    drift_alert_threshold: float = 0.25
    drift_cron: str = "0 2 * * 1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        enable_decoding=False,
    )

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, value: Any) -> list[str]:
        if value in (None, "", []):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        raise TypeError("api_keys must be a comma-separated string or list of strings")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
