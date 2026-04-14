from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select

from docintel.config import get_settings
from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.models.drift_report import DriftReport, DriftStatus
from docintel.models.query import Query, RetrievalStrategy
from docintel.models.retrieval import Retrieval
from docintel.services.drift.evidently_runner import resolve_drift_status
from docintel.services.drift.reporter import create_drift_report


def _embedding(index: int) -> list[float]:
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


class _StubEmbedder:
    def embed_texts(self, texts, batch_size: int = 16):
        embeddings = []
        for text in texts:
            offset = int(text.rsplit(" ", 1)[-1]) * 0.001
            if text.startswith("reference"):
                embeddings.append([0.05 + offset, 0.10 + offset, 0.15 + offset, 0.20 + offset])
            elif text.startswith("warning"):
                embeddings.append([0.22 + offset, 0.26 + offset, 0.30 + offset, 0.34 + offset])
            else:
                embeddings.append([0.80 + offset, 0.84 + offset, 0.88 + offset, 0.92 + offset])
        return embeddings


@pytest.fixture
def artifact_storage(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ARTIFACT_STORAGE_PATH", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


async def _seed_drift_fixture(session, *, now: datetime, current_prefix: str = "current", count: int = 40):
    document = Document(
        title="Drift Seed",
        source_uri="benchmark://drift",
        sha256=uuid.uuid4().hex,
        page_count=4,
        byte_size=4,
        status=DocumentStatus.READY,
    )
    session.add(document)
    await session.flush()

    chunks = [
        Chunk(
            document_id=document.id,
            ordinal=index,
            text=f"Chunk {index}",
            token_count=10,
            char_start=index * 50,
            char_end=index * 50 + 49,
            page_start=1,
            page_end=1,
            section_path=f"Article {index + 1}",
            embedding=_embedding(index),
            metadata_json={},
        )
        for index in range(4)
    ]
    session.add_all(chunks)
    await session.flush()

    reference_timestamp = now - timedelta(days=9)
    current_timestamp = now - timedelta(days=2)
    for index in range(count):
        await _create_query_with_retrievals(
            session,
            query_text=f"reference compliance question {index}",
            created_at=reference_timestamp + timedelta(minutes=index),
            chunks=chunks,
            fused_scores=[0.95, 0.80, 0.60, 0.40],
            rerank_scores=[0.94, 0.79, 0.58, 0.38],
            final_order=[0, 1, 2, 3],
        )
        await _create_query_with_retrievals(
            session,
            query_text=f"{current_prefix} compliance question {index}",
            created_at=current_timestamp + timedelta(minutes=index),
            chunks=chunks,
            fused_scores=[0.95, 0.80, 0.60, 0.40],
            rerank_scores=[0.18, 0.16, 0.12, 0.08],
            final_order=[3, 2, 1, 0],
        )
    await session.commit()


async def _create_query_with_retrievals(
    session,
    *,
    query_text: str,
    created_at: datetime,
    chunks: list[Chunk],
    fused_scores: list[float],
    rerank_scores: list[float],
    final_order: list[int],
):
    query = Query(
        query_text=query_text,
        strategy=RetrievalStrategy.HYBRID_RERANKED,
        top_k=len(chunks),
        rerank_top_n=len(chunks),
        alpha=0.5,
        rrf_k=60,
        latency_ms=120,
        metadata_json={},
        created_at=created_at,
    )
    session.add(query)
    await session.flush()

    for rank, chunk_index in enumerate(final_order, start=1):
        session.add(
            Retrieval(
                query_id=query.id,
                chunk_id=chunks[chunk_index].id,
                rank=rank,
                bm25_score=fused_scores[chunk_index] - 0.05,
                vector_score=fused_scores[chunk_index] - 0.02,
                fused_score=fused_scores[chunk_index],
                rerank_score=rerank_scores[chunk_index],
                created_at=created_at,
            )
        )


@pytest.mark.asyncio
async def test_drift_runner_computes_scores_on_seeded_data(postgres_db_session, artifact_storage, monkeypatch):
    now = datetime.now(timezone.utc)
    await _seed_drift_fixture(postgres_db_session, now=now)
    monkeypatch.setattr("docintel.services.drift.evidently_runner.get_embedder", lambda: _StubEmbedder())

    report = await create_drift_report(
        session=postgres_db_session,
        window_days=7,
        reference_window_days=7,
        now=now,
    )

    assert report.embedding_drift_score is not None
    assert report.query_drift_score is not None
    assert report.retrieval_quality_delta is not None
    assert report.status == DriftStatus.ALERT
    assert report.payload_json["metrics"]["rank_stability"]["delta"] is not None
    assert report.html_path is not None
    assert Path(report.html_path).exists()

    persisted_total = await postgres_db_session.scalar(select(func.count()).select_from(DriftReport))
    assert persisted_total == 1


@pytest.mark.asyncio
async def test_drift_endpoints_pagination(postgres_client, postgres_db_session, artifact_storage, monkeypatch):
    now = datetime.now(timezone.utc)
    await _seed_drift_fixture(postgres_db_session, now=now)
    monkeypatch.setattr("docintel.services.drift.evidently_runner.get_embedder", lambda: _StubEmbedder())

    first = await postgres_client.post(
        "/api/v1/drift/reports",
        headers={"X-API-Key": "dev-key-change-me"},
        json={"window_days": 7, "reference_window_days": 7},
    )
    second = await postgres_client.post(
        "/api/v1/drift/reports",
        headers={"X-API-Key": "dev-key-change-me"},
        json={"window_days": 7, "reference_window_days": 7},
    )

    assert first.status_code == 202
    assert second.status_code == 202

    response = await postgres_client.get(
        "/api/v1/drift/reports?page=1&per_page=1&status=alert",
        headers={"X-API-Key": "dev-key-change-me"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 1
    assert body["data"][0]["status"] == "alert"

    detail = await postgres_client.get(
        f"/api/v1/drift/reports/{first.json()['id']}",
        headers={"X-API-Key": "dev-key-change-me"},
    )
    assert detail.status_code == 200
    assert detail.json()["html_url"].startswith("file:///")


def test_drift_status_warning_at_threshold():
    assert resolve_drift_status(score=0.15, warning_threshold=0.15, alert_threshold=0.25) == DriftStatus.WARNING


def test_drift_status_alert_above_threshold():
    assert resolve_drift_status(score=0.251, warning_threshold=0.15, alert_threshold=0.25) == DriftStatus.ALERT
