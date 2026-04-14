from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import Base

if TYPE_CHECKING:
    from .eval_case import EvalCase


class EvalRunStatus(str, Enum):
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERRORED = "errored"


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_version: Mapped[str] = mapped_column(String(32), nullable=False)
    git_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    generation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    judge_model: Mapped[str] = mapped_column(String(128), nullable=False)
    retrieval_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EvalRunStatus] = mapped_column(
        SAEnum(
            EvalRunStatus,
            name="eval_run_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=EvalRunStatus.RUNNING,
    )
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cases_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    faithfulness_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    answer_relevancy_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    thresholds_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    cases: Mapped[list["EvalCase"]] = relationship(back_populates="run", cascade="all, delete-orphan")
