from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.models.chunk import Chunk
from docintel.models.document import Document

from .fusion import ChunkScore


async def vector_search(
    session: AsyncSession,
    query_vec: list[float],
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
) -> list[ChunkScore]:
    distance = Chunk.embedding.cosine_distance(query_vec)
    vector_score = (1.0 - distance).label("vector_score")

    stmt = (
        select(Chunk, Document.title.label("document_title"), vector_score, distance.label("distance"))
        .join(Document, Document.id == Chunk.document_id)
        .order_by(distance.asc(), Chunk.id.asc())
        .limit(top_k)
    )
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))

    rows = (await session.execute(stmt)).all()
    return [
        ChunkScore(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=document_title,
            ordinal=chunk.ordinal,
            text=chunk.text,
            section_path=chunk.section_path,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            rank=rank,
            vector_score=float(score) if score is not None else None,
        )
        for rank, (chunk, document_title, score, _distance) in enumerate(rows, start=1)
    ]
