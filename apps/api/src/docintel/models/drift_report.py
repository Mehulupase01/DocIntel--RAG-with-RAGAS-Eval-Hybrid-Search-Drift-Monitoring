from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SAEnum, Float, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .base import Base


class DriftStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"
    ALERT = "alert"


class DriftReport(Base):
    __tablename__ = "drift_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reference_window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    embedding_drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    query_drift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieval_quality_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[DriftStatus] = mapped_column(
        SAEnum(
            DriftStatus,
            name="drift_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=DriftStatus.OK,
    )
    html_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
