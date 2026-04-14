from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)
    strategy: str = Field(default="hybrid_reranked", pattern="^(vector_only|bm25_only|hybrid|hybrid_reranked)$")
    rerank_top_n: int = Field(default=50, ge=10, le=200)
    rrf_k: int = Field(default=60, ge=1, le=1000)
    document_ids: list[uuid.UUID] | None = None


class RetrievedChunk(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    ordinal: int
    text: str
    section_path: str | None
    page_start: int
    page_end: int
    rank: int
    bm25_score: float | None
    vector_score: float | None
    fused_score: float | None
    rerank_score: float | None


class SearchResponse(BaseModel):
    query_id: uuid.UUID
    results: list[RetrievedChunk]
    latency_ms: int
