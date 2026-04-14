from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class DriftReportCreate(BaseModel):
    window_days: int = 7
    reference_window_days: int = 7


class DriftReportOut(BaseModel):
    id: uuid.UUID
    window_start: datetime
    window_end: datetime
    reference_window_start: datetime
    reference_window_end: datetime
    embedding_drift_score: float | None
    query_drift_score: float | None
    retrieval_quality_delta: float | None
    status: str
    html_path: str | None
    html_url: str | None = None
    created_at: datetime
