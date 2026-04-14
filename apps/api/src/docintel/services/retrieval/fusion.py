from __future__ import annotations

import uuid
from dataclasses import dataclass, replace


@dataclass(slots=True)
class ChunkScore:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    ordinal: int
    text: str
    section_path: str | None
    page_start: int
    page_end: int
    rank: int | None = None
    bm25_score: float | None = None
    vector_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None


def reciprocal_rank_fusion(ranked_lists: list[list[ChunkScore]], k: int = 60) -> list[ChunkScore]:
    merged: dict[uuid.UUID, ChunkScore] = {}
    fused_scores: dict[uuid.UUID, float] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, start=1):
            fused_scores[item.chunk_id] = fused_scores.get(item.chunk_id, 0.0) + (1.0 / (k + rank))
            if item.chunk_id not in merged:
                merged[item.chunk_id] = replace(item)
                continue

            current = merged[item.chunk_id]
            if item.bm25_score is not None:
                current.bm25_score = item.bm25_score
            if item.vector_score is not None:
                current.vector_score = item.vector_score
            if item.rerank_score is not None:
                current.rerank_score = item.rerank_score

    ranked_results = sorted(
        (replace(item, fused_score=fused_scores[item.chunk_id]) for item in merged.values()),
        key=lambda item: item.fused_score or 0.0,
        reverse=True,
    )
    return [replace(item, rank=rank) for rank, item in enumerate(ranked_results, start=1)]
