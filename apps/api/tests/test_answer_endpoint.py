from __future__ import annotations

import uuid
from dataclasses import replace

import httpx
import pytest
from docintel.models.answer import Answer
from docintel.models.chunk import Chunk
from docintel.models.citation import Citation
from docintel.models.document import Document, DocumentStatus
from docintel.models.query import Query
from docintel.models.retrieval import Retrieval
from docintel.services.generation.llm_client import LLMProviderError, OpenRouterClient
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
        preferred = ("high-risk", "annex iii") if "high-risk" in query.lower() else ("prohibited", "article 5")
        reranked = []
        for candidate in candidates:
            score = sum(1.0 for term in preferred if term in candidate.text.lower()) or 0.2
            reranked.append(replace(candidate, rerank_score=score))
        reranked.sort(key=lambda item: item.rerank_score or 0.0, reverse=True)
        return [replace(item, rank=rank) for rank, item in enumerate(reranked, start=1)]


async def _seed_answer_fixture(session):
    document = Document(
        title="Seed Document",
        source_uri="benchmark://answer",
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
            text="A high-risk AI system is defined in Article 6 by reference to Annex III.",
            token_count=14,
            char_start=0,
            char_end=71,
            page_start=1,
            page_end=1,
            section_path="Article 6",
            embedding=_embedding(0),
            metadata_json={},
        ),
        Chunk(
            document_id=document.id,
            ordinal=1,
            text="Annex III lists use cases that classify a high-risk AI system.",
            token_count=11,
            char_start=72,
            char_end=136,
            page_start=1,
            page_end=1,
            section_path="Annex III",
            embedding=_embedding(2),
            metadata_json={},
        ),
        Chunk(
            document_id=document.id,
            ordinal=2,
            text="Providers must maintain quality management systems for high-risk AI systems.",
            token_count=11,
            char_start=137,
            char_end=216,
            page_start=2,
            page_end=2,
            section_path="Article 17",
            embedding=_embedding(0),
            metadata_json={},
        ),
    ]
    session.add_all(chunks)
    await session.commit()
    return document, chunks


def _success_transport() -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/chat/completions")
        return httpx.Response(
            200,
            json={
                "id": "gen-1",
                "model": "minimax/minimax-m2.5:free",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": (
                                "A high-risk AI system is defined by Article 6 [c#1] "
                                "and further illustrated by Annex III use cases [c#2]."
                            ),
                        },
                    }
                ],
                "usage": {"prompt_tokens": 123, "completion_tokens": 45},
            },
        )

    return httpx.MockTransport(handler)


def _provider_error_transport() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "error": {
                    "message": "Provider returned error",
                    "code": 429,
                }
            },
        )

    return httpx.MockTransport(handler)


def _output_text_transport() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen-2",
                "model": "anthropic/claude-haiku-4.5",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "output_text", "text": "Structured success."}],
                        },
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 3},
            },
        )

    return httpx.MockTransport(handler)


def _dict_text_transport() -> httpx.MockTransport:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen-3",
                "model": "openai/gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": {"text": "Dict success."},
                        },
                    }
                ],
                "usage": {"prompt_tokens": 9, "completion_tokens": 2},
            },
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_openrouter_client_raises_on_provider_error_payload():
    async with httpx.AsyncClient(transport=_provider_error_transport(), base_url="https://openrouter.ai/api/v1") as http_client:
        client = OpenRouterClient(api_key="test-key", http_client=http_client, max_retries=1)
        with pytest.raises(LLMProviderError, match="provider error 429"):
            await client.generate(
                messages=[{"role": "user", "content": "ping"}],
                model="minimax/minimax-m2.5:free",
                temperature=0.0,
                max_tokens=16,
            )


@pytest.mark.asyncio
async def test_openrouter_client_accepts_output_text_parts():
    async with httpx.AsyncClient(transport=_output_text_transport(), base_url="https://openrouter.ai/api/v1") as http_client:
        client = OpenRouterClient(api_key="test-key", http_client=http_client, max_retries=1)
        result = await client.generate(
            messages=[{"role": "user", "content": "ping"}],
            model="anthropic/claude-haiku-4.5",
            temperature=0.0,
            max_tokens=16,
        )

    assert result.text == "Structured success."
    assert result.model == "anthropic/claude-haiku-4.5"


@pytest.mark.asyncio
async def test_openrouter_client_accepts_dict_text_content():
    async with httpx.AsyncClient(transport=_dict_text_transport(), base_url="https://openrouter.ai/api/v1") as http_client:
        client = OpenRouterClient(api_key="test-key", http_client=http_client, max_retries=1)
        result = await client.generate(
            messages=[{"role": "user", "content": "ping"}],
            model="openai/gpt-4o-mini",
            temperature=0.0,
            max_tokens=16,
        )

    assert result.text == "Dict success."
    assert result.model == "openai/gpt-4o-mini"


@pytest.mark.asyncio
async def test_answer_endpoint_returns_citations_with_chunk_metadata(postgres_client, postgres_db_session, monkeypatch):
    _document, chunks = await _seed_answer_fixture(postgres_db_session)
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_reranker", lambda: _StubReranker())

    async with httpx.AsyncClient(transport=_success_transport(), base_url="https://openrouter.ai/api/v1") as http_client:
        client = OpenRouterClient(api_key="test-key", http_client=http_client, max_retries=1)
        monkeypatch.setattr("docintel.services.generation.answerer.get_openrouter_client", lambda: client)

        response = await postgres_client.post(
            "/api/v1/answer",
            headers={"X-API-Key": "dev-key-change-me"},
            json={"query": "Define high-risk AI system per the EU AI Act", "top_k": 2},
        )

    assert response.status_code == 200
    body = response.json()
    assert "[c#" not in body["answer"]
    assert len(body["citations"]) == 2
    assert body["citations"][0]["chunk_id"] == str(chunks[0].id)
    assert body["citations"][0]["document_title"] == "Seed Document"
    assert body["citations"][0]["section_path"] == "Article 6"
    assert body["contexts"][0]["chunk_id"] == str(chunks[0].id)
    assert body["model"] == "minimax/minimax-m2.5:free"
    assert body["prompt_tokens"] == 123
    assert body["completion_tokens"] == 45


@pytest.mark.asyncio
async def test_answer_persists_query_retrievals_answer_citations(postgres_client, postgres_db_session, monkeypatch):
    await _seed_answer_fixture(postgres_db_session)
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_reranker", lambda: _StubReranker())

    async with httpx.AsyncClient(transport=_success_transport(), base_url="https://openrouter.ai/api/v1") as http_client:
        client = OpenRouterClient(api_key="test-key", http_client=http_client, max_retries=1)
        monkeypatch.setattr("docintel.services.generation.answerer.get_openrouter_client", lambda: client)

        response = await postgres_client.post(
            "/api/v1/answer",
            headers={"X-API-Key": "dev-key-change-me"},
            json={"query": "Define high-risk AI system per the EU AI Act", "top_k": 2},
        )

    assert response.status_code == 200

    query_count = await postgres_db_session.scalar(select(func.count(Query.id)))
    retrieval_count = await postgres_db_session.scalar(select(func.count(Retrieval.id)))
    answer_count = await postgres_db_session.scalar(select(func.count(Answer.id)))
    citation_count = await postgres_db_session.scalar(select(func.count(Citation.id)))

    assert query_count == 1
    assert retrieval_count == 2
    assert answer_count == 1
    assert citation_count == 2


@pytest.mark.asyncio
async def test_answer_llm_502_on_provider_error(postgres_client, postgres_db_session, monkeypatch):
    await _seed_answer_fixture(postgres_db_session)
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_embedder", lambda: _StubEmbedder())
    monkeypatch.setattr("docintel.services.retrieval.hybrid.get_reranker", lambda: _StubReranker())

    class _FailingClient:
        async def generate(self, **_kwargs):
            raise LLMProviderError("upstream failure")

    monkeypatch.setattr("docintel.services.generation.answerer.get_openrouter_client", lambda: _FailingClient())

    response = await postgres_client.post(
        "/api/v1/answer",
        headers={"X-API-Key": "dev-key-change-me"},
        json={"query": "Define high-risk AI system per the EU AI Act", "top_k": 2},
    )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "LLM_PROVIDER_ERROR"
