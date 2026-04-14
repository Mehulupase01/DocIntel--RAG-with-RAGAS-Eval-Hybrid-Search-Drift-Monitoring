from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from .search import RetrievedChunk


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)
    strategy: Literal["vector_only", "bm25_only", "hybrid", "hybrid_reranked"] = "hybrid_reranked"
    model: str | None = None
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1024, ge=64, le=4096)


class CitationOut(BaseModel):
    ordinal: int
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    page_start: int
    page_end: int
    section_path: str | None
    span_text: str


class AnswerResponse(BaseModel):
    query_id: uuid.UUID
    answer_id: uuid.UUID
    answer: str
    citations: list[CitationOut]
    contexts: list[RetrievedChunk]
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
