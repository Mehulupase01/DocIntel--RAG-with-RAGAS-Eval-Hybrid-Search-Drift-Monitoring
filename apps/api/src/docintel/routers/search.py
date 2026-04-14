from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.auth import require_api_key
from docintel.database import get_db
from docintel.models.query import RetrievalStrategy
from docintel.schemas.search import RetrievedChunk, SearchRequest, SearchResponse
from docintel.services.retrieval.hybrid import hybrid_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> SearchResponse:
    result = await hybrid_search(
        session=db,
        query=request.query,
        strategy=RetrievalStrategy(request.strategy),
        top_k=request.top_k,
        rerank_top_n=request.rerank_top_n,
        rrf_k=request.rrf_k,
        document_ids=request.document_ids,
    )
    return SearchResponse(
        query_id=result.query_id,
        results=[
            RetrievedChunk(
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                document_title=item.document_title,
                ordinal=item.ordinal,
                text=item.text,
                section_path=item.section_path,
                page_start=item.page_start,
                page_end=item.page_end,
                rank=item.rank or rank,
                bm25_score=item.bm25_score,
                vector_score=item.vector_score,
                fused_score=item.fused_score,
                rerank_score=item.rerank_score,
            )
            for rank, item in enumerate(result.results, start=1)
        ],
        latency_ms=result.latency_ms,
    )
