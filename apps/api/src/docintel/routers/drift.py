from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.auth import require_api_key
from docintel.database import get_db
from docintel.models.drift_report import DriftReport, DriftStatus
from docintel.schemas.common import PageMeta, Paginated
from docintel.schemas.drift import DriftReportCreate, DriftReportOut
from docintel.services.drift.reporter import create_drift_report

router = APIRouter(prefix="/drift", tags=["drift"])


@router.post("/reports", response_model=DriftReportOut, status_code=status.HTTP_202_ACCEPTED)
async def generate_drift_report(
    request: DriftReportCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> DriftReportOut:
    report = await create_drift_report(
        session=db,
        window_days=request.window_days,
        reference_window_days=request.reference_window_days,
    )
    return _to_drift_report_out(report)


@router.get("/reports", response_model=Paginated[DriftReportOut])
async def list_drift_reports(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    status_filter: Annotated[DriftStatus | None, Query(alias="status")] = None,
) -> Paginated[DriftReportOut]:
    filters = []
    if status_filter is not None:
        filters.append(DriftReport.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(DriftReport).where(*filters))
    stmt = (
        select(DriftReport)
        .where(*filters)
        .order_by(DriftReport.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = list((await db.scalars(stmt)).all())
    return Paginated[DriftReportOut](
        data=[_to_drift_report_out(row) for row in rows],
        meta=PageMeta(page=page, per_page=per_page, total=int(total or 0)),
    )


@router.get("/reports/{report_id}", response_model=DriftReportOut)
async def get_drift_report(
    report_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> DriftReportOut:
    report = await db.get(DriftReport, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drift report not found")
    return _to_drift_report_out(report)


def _to_drift_report_out(report: DriftReport) -> DriftReportOut:
    html_url = Path(report.html_path).resolve().as_uri() if report.html_path else None
    return DriftReportOut(
        id=report.id,
        window_start=report.window_start,
        window_end=report.window_end,
        reference_window_start=report.reference_window_start,
        reference_window_end=report.reference_window_end,
        embedding_drift_score=report.embedding_drift_score,
        query_drift_score=report.query_drift_score,
        retrieval_quality_delta=report.retrieval_quality_delta,
        status=report.status.value,
        html_path=report.html_path,
        html_url=html_url,
        created_at=report.created_at,
    )
