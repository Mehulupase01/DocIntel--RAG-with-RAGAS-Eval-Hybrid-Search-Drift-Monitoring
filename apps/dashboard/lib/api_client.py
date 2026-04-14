from __future__ import annotations

import os

import httpx

SEARCH_STRATEGIES = [
    "vector_only",
    "bm25_only",
    "hybrid",
    "hybrid_reranked",
]


def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")


def get_api_key() -> str:
    return os.getenv("API_KEY", "dev-key-change-me")


def run_search(*, query: str, strategy: str, top_k: int) -> dict:
    response = httpx.post(
        f"{get_api_base_url()}/search",
        headers={"X-API-Key": get_api_key()},
        json={
            "query": query,
            "strategy": strategy,
            "top_k": top_k,
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def run_search_matrix(*, query: str, top_k: int) -> dict[str, dict]:
    return {strategy: run_search(query=query, strategy=strategy, top_k=top_k) for strategy in SEARCH_STRATEGIES}
