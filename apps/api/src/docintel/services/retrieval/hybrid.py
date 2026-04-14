from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from docintel.models.query import Query, RetrievalStrategy
from docintel.models.retrieval import Retrieval
from docintel.services.ingestion.embedder import get_embedder
from docintel.services.monitoring.metrics import record_retrieval_scores

from .bm25 import bm25_search
from .fusion import ChunkScore, reciprocal_rank_fusion
from .reranker import get_reranker
from .vector import vector_search


@dataclass(slots=True)
class SearchResult:
    query_id: uuid.UUID
    results: list[ChunkScore]
    latency_ms: int


async def hybrid_search(
    session: AsyncSession,
    query: str,
    strategy: RetrievalStrategy,
    top_k: int,
    rerank_top_n: int,
    rrf_k: int,
    document_ids: list[uuid.UUID] | None = None,
) -> SearchResult:
    start = perf_counter()
    candidate_k = max(top_k, rerank_top_n if strategy == RetrievalStrategy.HYBRID_RERANKED else top_k)

    if strategy == RetrievalStrategy.BM25_ONLY:
        results = await bm25_search(session, query, top_k, document_ids=document_ids)
    elif strategy == RetrievalStrategy.VECTOR_ONLY:
        query_vec = get_embedder().embed_texts([query])[0]
        results = await vector_search(session, query_vec, top_k, document_ids=document_ids)
    else:
        query_vec = get_embedder().embed_texts([query])[0]
        bm25_results = await bm25_search(session, query, candidate_k, document_ids=document_ids)
        vector_results = await vector_search(session, query_vec, candidate_k, document_ids=document_ids)
        fused_results = reciprocal_rank_fusion([bm25_results, vector_results], k=rrf_k)
        if strategy == RetrievalStrategy.HYBRID_RERANKED:
            rerank_candidates = fused_results[: min(rerank_top_n, len(fused_results))]
            results = get_reranker().rerank(query, rerank_candidates)[:top_k]
        else:
            results = fused_results[:top_k]
            for rank, item in enumerate(results, start=1):
                item.rank = rank

    latency_ms = int((perf_counter() - start) * 1000)
    query_row = Query(
        query_text=query,
        strategy=strategy,
        top_k=top_k,
        rerank_top_n=rerank_top_n,
        rrf_k=rrf_k,
        latency_ms=latency_ms,
        metadata_json={"document_ids": [str(document_id) for document_id in document_ids] if document_ids else []},
    )
    session.add(query_row)
    await session.flush()

    session.add_all(
        Retrieval(
            query_id=query_row.id,
            chunk_id=result.chunk_id,
            rank=result.rank or rank,
            bm25_score=result.bm25_score,
            vector_score=result.vector_score,
            fused_score=result.fused_score,
            rerank_score=result.rerank_score,
        )
        for rank, result in enumerate(results, start=1)
    )
    await session.commit()
    record_retrieval_scores(strategy.value, results)

    return SearchResult(query_id=query_row.id, results=results, latency_ms=latency_ms)
