from __future__ import annotations

import hashlib
import uuid

import pytest
from docintel.models.chunk import Chunk
from docintel.models.document import Document
from sqlalchemy import func, select


class _StubEmbedder:
    def embed_texts(self, texts):
        return [[1.0 / 384.0] * 384 for _ in texts]


@pytest.mark.asyncio
async def test_documents_upload_pdf_201(postgres_client, tiny_pdf_bytes, monkeypatch):
    monkeypatch.setattr("docintel.services.ingestion.pipeline.get_embedder", lambda: _StubEmbedder())

    response = await postgres_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "dev-key-change-me"},
        files={"file": ("tiny_pdf.pdf", tiny_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sha256"] == hashlib.sha256(tiny_pdf_bytes).hexdigest()
    assert body["page_count"] == 3
    assert body["chunk_count"] > 0


@pytest.mark.asyncio
async def test_documents_upload_duplicate_409(postgres_client, tiny_pdf_bytes, monkeypatch):
    monkeypatch.setattr("docintel.services.ingestion.pipeline.get_embedder", lambda: _StubEmbedder())

    await postgres_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "dev-key-change-me"},
        files={"file": ("tiny_pdf.pdf", tiny_pdf_bytes, "application/pdf")},
    )
    response = await postgres_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "dev-key-change-me"},
        files={"file": ("tiny_pdf.pdf", tiny_pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_DOCUMENT"


@pytest.mark.asyncio
async def test_documents_list_pagination(postgres_client, tiny_pdf_bytes, monkeypatch):
    monkeypatch.setattr("docintel.services.ingestion.pipeline.get_embedder", lambda: _StubEmbedder())

    variant_bytes = tiny_pdf_bytes + b"\n% variant\n"
    for index, payload in enumerate((tiny_pdf_bytes, variant_bytes), start=1):
        response = await postgres_client.post(
            "/api/v1/documents",
            headers={"X-API-Key": "dev-key-change-me"},
            data={"title": f"Doc {index}"},
            files={"file": (f"tiny_{index}.pdf", payload, "application/pdf")},
        )
        assert response.status_code == 201

    response = await postgres_client.get("/api/v1/documents?page=1&per_page=1")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 2
    assert len(body["data"]) == 1


@pytest.mark.asyncio
async def test_documents_get_404(postgres_client):
    response = await postgres_client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_documents_delete_204_cascades_chunks(postgres_client, postgres_db_session, tiny_pdf_bytes, monkeypatch):
    monkeypatch.setattr("docintel.services.ingestion.pipeline.get_embedder", lambda: _StubEmbedder())

    create_response = await postgres_client.post(
        "/api/v1/documents",
        headers={"X-API-Key": "dev-key-change-me"},
        files={"file": ("tiny_pdf.pdf", tiny_pdf_bytes, "application/pdf")},
    )
    document_id = uuid.UUID(create_response.json()["id"])

    document_count = await postgres_db_session.scalar(
        select(func.count(Document.id)).where(Document.id == document_id)
    )
    chunk_count = await postgres_db_session.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )
    assert document_count == 1
    assert chunk_count and chunk_count > 0

    delete_response = await postgres_client.delete(
        f"/api/v1/documents/{document_id}",
        headers={"X-API-Key": "dev-key-change-me"},
    )
    assert delete_response.status_code == 204

    get_response = await postgres_client.get(f"/api/v1/documents/{document_id}")
    assert get_response.status_code == 404

    remaining_chunks = await postgres_db_session.scalar(
        select(func.count(Chunk.id)).where(Chunk.document_id == document_id)
    )
    assert remaining_chunks == 0
