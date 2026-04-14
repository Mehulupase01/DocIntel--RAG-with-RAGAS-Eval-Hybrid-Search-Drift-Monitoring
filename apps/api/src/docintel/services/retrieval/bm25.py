from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.models.chunk import Chunk
from docintel.models.document import Document

from .fusion import ChunkScore


async def bm25_search(
    session: AsyncSession,
    query: str,
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
) -> list[ChunkScore]:
    ts_query = func.plainto_tsquery("english", query)
    bm25_score = func.ts_rank_cd(Chunk.tsv, ts_query)

    stmt = (
        select(Chunk, Document.title.label("document_title"), bm25_score.label("bm25_score"))
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.tsv.bool_op("@@")(ts_query))
        .order_by(bm25_score.desc(), Chunk.id.asc())
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
            bm25_score=float(score) if score is not None else None,
        )
        for rank, (chunk, document_title, score) in enumerate(rows, start=1)
    ]
