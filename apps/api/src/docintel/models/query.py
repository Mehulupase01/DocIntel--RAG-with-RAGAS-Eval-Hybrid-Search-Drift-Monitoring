from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base


class RetrievalStrategy(str, Enum):
    VECTOR_ONLY = "vector_only"
    BM25_ONLY = "bm25_only"
    HYBRID = "hybrid"
    HYBRID_RERANKED = "hybrid_reranked"


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    strategy: Mapped[RetrievalStrategy] = mapped_column(
        SAEnum(
            RetrievalStrategy,
            name="retrieval_strategy",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    rerank_top_n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alpha: Mapped[float | None] = mapped_column(Float, nullable=True)
    rrf_k: Mapped[int | None] = mapped_column(Integer, nullable=True, default=60)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    retrievals: Mapped[list["Retrieval"]] = relationship(back_populates="query", cascade="all, delete-orphan")
