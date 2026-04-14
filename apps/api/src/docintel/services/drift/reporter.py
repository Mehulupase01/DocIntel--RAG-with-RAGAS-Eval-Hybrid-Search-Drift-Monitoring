from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config import get_settings
from docintel.models.drift_report import DriftReport

from .evidently_runner import DriftAnalysisResult, run_drift_analysis


async def create_drift_report(
    *,
    session: AsyncSession,
    window_days: int,
    reference_window_days: int,
    now=None,
    embedder=None,
) -> DriftReport:
    analysis = await run_drift_analysis(
        session=session,
        window_days=window_days,
        reference_window_days=reference_window_days,
        now=now,
        embedder=embedder,
    )
    return await persist_drift_report(session=session, analysis=analysis)


async def persist_drift_report(*, session: AsyncSession, analysis: DriftAnalysisResult) -> DriftReport:
    settings = get_settings()
    report_id = uuid.uuid4()
    html_path = Path(settings.artifact_storage_path) / "drift" / f"{report_id}.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(analysis.html, encoding="utf-8")

    report = DriftReport(
        id=report_id,
        window_start=analysis.window_start,
        window_end=analysis.window_end,
        reference_window_start=analysis.reference_window_start,
        reference_window_end=analysis.reference_window_end,
        embedding_drift_score=analysis.embedding_drift_score,
        query_drift_score=analysis.query_drift_score,
        retrieval_quality_delta=analysis.retrieval_quality_delta,
        status=analysis.status,
        html_path=str(html_path),
        payload_json=analysis.payload_json,
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report
