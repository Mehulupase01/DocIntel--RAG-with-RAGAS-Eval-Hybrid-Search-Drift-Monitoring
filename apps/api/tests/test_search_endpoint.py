from __future__ import annotations

import uuid
from dataclasses import replace

import pytest
from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.models.query import Query
from docintel.models.retrieval import Retrieval
from sqlalchemy import func, select


def _embedding(index: int) -> list[float]:
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


class _StubEmbedder:
    def embed_texts(self, texts):
        query = texts[0].lower()
        if "prohibited" in query:
            return [_embedding(1)]
        return [_embedding(0)]


class _StubReranker:
    def rerank(self, query, candidates):
        preferred = "high-risk" if "high-risk" in query.lower() else "prohibited"
        scored = []
        for candidate in candidates:
            score = 1.0 if preferred in candidate.text.lower() else 0.2
            scored.append(replace(candidate, rerank_score=score))
        scored.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return [replace(item, rank=rank) for rank, item in enumerate(scored, start=1)]


async def _seed_search_fixture(session):
    document = Document(
        title="Seed Document",
        source_uri="benchmark://search",
        sha256=uuid.uuid4().hex,
        page_count=2,
        byte_size=2,
        status=DocumentStatus.READY,
    )
    session.add(document)
    await session.flush()

    chunks = [
        Chunk(
            document_id=document.id,
            ordinal=0,
            text="A high-risk AI system is defined in Article 6 and Annex III.",
            token_count=12,
            char_start=0,
            char_end=60,
            page_start=1,
            page_end=1,
            section_path="Article 6",
            embedding=_embedding(0),
            metadata_json={},
        ),
        Chunk(
            document_id=document.id,
            ordinal=1,
            text="Prohibited AI practices are listed in Article 5.",
            token_count=9,
            char_start=61,
            char_end=110,
            page_start=1,
            page_end=1,
            section_path="Article 5",
            embedding=_embedding(1),
            metadata_json={},
        ),
        Chunk(
            document_id=document.id,
            ordinal=2,
            text="The Regulation also contains general provisions and scope rules.",
            token_count=10,
            char_start=111,
            char_end=172,
            page_start=2,
            page_end=2,
            section_path="Title I",
            embedding=_embedding(2),
            metadata_json={},
        ),
    ]
    session.add_all(chunks)
    await session.commit()
    return document, chunks


@pytest.mark.asyncio
async def test_search_endpoint_strategies(postgres_client, postgres_db_session, monkeypatch):
    _document, chunks = await _seed_search_fixture(postgres_db_session)
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_reranker", lambda: _StubReranker())

    cases = [
        ("vector_only", "high-risk", {"vector_score"}, {"bm25_score", "fused_score", "rerank_score"}),
        ("bm25_only", "high-risk", {"bm25_score"}, {"vector_score", "fused_score", "rerank_score"}),
        ("hybrid", "high-risk", {"bm25_score", "vector_score", "fused_score"}, {"rerank_score"}),
        ("hybrid_reranked", "high-risk", {"bm25_score", "vector_score", "fused_score", "rerank_score"}, set()),
    ]

    for strategy, query, expected_keys, forbidden_keys in cases:
        response = await postgres_client.post(
            "/api/v1/search",
            headers={"X-API-Key": "dev-key-change-me"},
            json={"query": query, "strategy": strategy, "top_k": 2},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["results"]
        top_result = body["results"][0]
        assert top_result["chunk_id"] == str(chunks[0].id)
        for key in expected_keys:
            assert top_result[key] is not None
        for key in forbidden_keys:
            assert top_result[key] is None


@pytest.mark.asyncio
async def test_search_persists_query_and_retrievals(postgres_client, postgres_db_session, monkeypatch):
    await _seed_search_fixture(postgres_db_session)
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_reranker", lambda: _StubReranker())

    response = await postgres_client.post(
        "/api/v1/search",
        headers={"X-API-Key": "dev-key-change-me"},
        json={"query": "What is a high-risk AI system?", "strategy": "hybrid_reranked", "top_k": 2},
    )
    assert response.status_code == 200

    query_count = await postgres_db_session.scalar(select(func.count(Query.id)))
    retrieval_count = await postgres_db_session.scalar(select(func.count(Retrieval.id)))
    assert query_count == 1
    assert retrieval_count == 2


@pytest.mark.asyncio
async def test_search_invalid_strategy_422(postgres_client):
    response = await postgres_client.post(
        "/api/v1/search",
        headers={"X-API-Key": "dev-key-change-me"},
        json={"query": "high-risk", "strategy": "bad_strategy", "top_k": 2},
    )

    assert response.status_code == 422
