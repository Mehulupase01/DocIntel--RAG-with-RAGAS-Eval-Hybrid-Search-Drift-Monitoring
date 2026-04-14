from __future__ import annotations

import uuid

from docintel.services.retrieval.fusion import ChunkScore, reciprocal_rank_fusion


def _chunk_score(seed: int, *, bm25_score: float | None = None, vector_score: float | None = None) -> ChunkScore:
    chunk_id = uuid.UUID(int=seed)
    return ChunkScore(
        chunk_id=chunk_id,
        document_id=uuid.UUID(int=seed + 100),
        document_title=f"Doc {seed}",
        ordinal=seed,
        text=f"Chunk {seed}",
        section_path=None,
        page_start=1,
        page_end=1,
        bm25_score=bm25_score,
        vector_score=vector_score,
    )


def test_reciprocal_rank_fusion():
    bm25_results = [_chunk_score(1, bm25_score=0.9), _chunk_score(2, bm25_score=0.7)]
    vector_results = [_chunk_score(2, vector_score=0.99), _chunk_score(1, vector_score=0.8)]

    results = reciprocal_rank_fusion([bm25_results, vector_results], k=60)

    assert len(results) == 2
    assert results[0].fused_score is not None
    assert {result.chunk_id for result in results} == {bm25_results[0].chunk_id, bm25_results[1].chunk_id}
