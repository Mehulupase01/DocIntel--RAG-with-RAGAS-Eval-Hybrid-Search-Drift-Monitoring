from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

from sentence_transformers import CrossEncoder

from docintel.config import get_settings

from .fusion import ChunkScore


class Reranker:
    def __init__(self, model: CrossEncoder | None = None) -> None:
        settings = get_settings()
        self.model = model or CrossEncoder(settings.reranker_model, device="cpu")

    def rerank(self, query: str, candidates: list[ChunkScore]) -> list[ChunkScore]:
        if not candidates:
            return []

        pairs = [(query, candidate.text) for candidate in candidates]
        scores = self.model.predict(pairs)
        reranked = [
            replace(candidate, rerank_score=float(score))
            for candidate, score in zip(candidates, scores, strict=True)
        ]
        reranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return [replace(item, rank=rank) for rank, item in enumerate(reranked, start=1)]


@lru_cache
def get_reranker() -> Reranker:
    return Reranker()
