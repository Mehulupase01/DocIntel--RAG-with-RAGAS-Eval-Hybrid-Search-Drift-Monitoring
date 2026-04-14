from __future__ import annotations

import uuid

import pytest

from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.services.retrieval.vector import vector_search


def _embedding(index: int) -> list[float]:
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


@pytest.mark.asyncio
async def test_vector(postgres_db_session):
    document = Document(
        title="Seed Document",
        source_uri="benchmark://seed",
        sha256=uuid.uuid4().hex,
        page_count=1,
        byte_size=1,
        status=DocumentStatus.READY,
    )
    postgres_db_session.add(document)
    await postgres_db_session.flush()

    chunks = [
        Chunk(
            document_id=document.id,
            ordinal=0,
            text="Definitions for high-risk AI systems.",
            token_count=6,
            char_start=0,
            char_end=36,
            page_start=1,
            page_end=1,
            section_path="Article 6",
            embedding=_embedding(0),
            metadata_json={},
        ),
        Chunk(
            document_id=document.id,
            ordinal=1,
            text="Prohibited AI practices are listed elsewhere.",
            token_count=7,
            char_start=37,
            char_end=82,
            page_start=1,
            page_end=1,
            section_path="Article 5",
            embedding=_embedding(1),
            metadata_json={},
        ),
    ]
    postgres_db_session.add_all(chunks)
    await postgres_db_session.commit()

    results = await vector_search(postgres_db_session, _embedding(0), top_k=2)

    assert results
    assert results[0].chunk_id == chunks[0].id
    assert results[0].vector_score is not None
