from __future__ import annotations

import uuid
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config import get_settings
from docintel.models.answer import Answer
from docintel.models.citation import Citation
from docintel.models.query import RetrievalStrategy
from docintel.schemas.answer import AnswerRequest, CitationOut
from docintel.schemas.search import RetrievedChunk
from docintel.services.generation.citation_extractor import extract_citations
from docintel.services.generation.llm_client import OpenRouterClient, get_openrouter_client
from docintel.services.generation.prompt import build_answer_prompt
from docintel.services.retrieval.hybrid import hybrid_search


@dataclass(slots=True)
class AnswerResult:
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


async def answer_question(
    *,
    session: AsyncSession,
    request: AnswerRequest,
    client: OpenRouterClient | None = None,
) -> AnswerResult:
    start = perf_counter()
    settings = get_settings()
    retrieval = await hybrid_search(
        session=session,
        query=request.query,
        strategy=RetrievalStrategy(request.strategy),
        top_k=request.top_k,
        rerank_top_n=settings.default_rerank_top_n,
        rrf_k=settings.default_rrf_k,
    )
    contexts = [_to_retrieved_chunk(item, rank) for rank, item in enumerate(retrieval.results, start=1)]

    system_prompt, user_prompt, prompt_text = build_answer_prompt(request.query, contexts)
    llm_client = client or get_openrouter_client()
    model = request.model or settings.default_generation_model
    generation = await llm_client.generate(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        model=model,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    answer_text, extracted_citations = extract_citations(generation.text, contexts)
    latency_ms = int((perf_counter() - start) * 1000)

    answer_row = Answer(
        query_id=retrieval.query_id,
        model=generation.model,
        prompt_text=prompt_text,
        response_text=answer_text,
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
        cost_usd=generation.cost_usd,
        latency_ms=latency_ms,
        finish_reason=generation.finish_reason,
        metadata_json={"llm_latency_ms": generation.latency_ms},
    )
    session.add(answer_row)
    await session.flush()

    citation_rows = [
        Citation(
            answer_id=answer_row.id,
            chunk_id=citation.context.chunk_id,
            ordinal=citation.ordinal,
            span_text=citation.span_text,
        )
        for citation in extracted_citations
    ]
    session.add_all(citation_rows)
    await session.commit()

    return AnswerResult(
        query_id=retrieval.query_id,
        answer_id=answer_row.id,
        answer=answer_text,
        citations=[
            CitationOut(
                ordinal=citation.ordinal,
                chunk_id=citation.context.chunk_id,
                document_id=citation.context.document_id,
                document_title=citation.context.document_title,
                page_start=citation.context.page_start,
                page_end=citation.context.page_end,
                section_path=citation.context.section_path,
                span_text=citation.span_text,
            )
            for citation in extracted_citations
        ],
        contexts=contexts,
        model=generation.model,
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
        cost_usd=generation.cost_usd,
        latency_ms=latency_ms,
    )


def _to_retrieved_chunk(item, rank: int) -> RetrievedChunk:
    return RetrievedChunk(
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
