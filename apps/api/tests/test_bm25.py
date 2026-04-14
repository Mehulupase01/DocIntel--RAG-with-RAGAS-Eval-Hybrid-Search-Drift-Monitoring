from __future__ import annotations

import uuid

import pytest
from docintel.models.chunk import Chunk
from docintel.models.document import Document, DocumentStatus
from docintel.services.retrieval.bm25 import bm25_search


def _embedding(index: int) -> list[float]:
    vector = [0.0] * 384
    vector[index] = 1.0
    return vector


@pytest.mark.asyncio
async def test_bm25(postgres_db_session):
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
            text="General provisions describe the purpose and scope of the Regulation.",
            token_count=10,
            char_start=61,
            char_end=125,
            page_start=1,
            page_end=1,
            section_path="Title I",
            embedding=_embedding(1),
            metadata_json={},
        ),
    ]
    postgres_db_session.add_all(chunks)
    await postgres_db_session.commit()

    results = await bm25_search(postgres_db_session, "high-risk AI system", top_k=2)

    assert results
    assert results[0].chunk_id == chunks[0].id
    assert results[0].bm25_score is not None
