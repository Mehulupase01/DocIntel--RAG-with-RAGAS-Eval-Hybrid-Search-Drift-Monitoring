from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.auth import require_api_key
from docintel.database import get_db, get_session_factory
from docintel.models.eval_case import EvalCase
from docintel.models.eval_run import EvalRun, EvalRunStatus
from docintel.schemas.common import PageMeta, Paginated
from docintel.schemas.eval import EvalCaseOut, EvalRunCreate, EvalRunOut
from docintel.services.evaluation.ragas_runner import run_eval_suite

router = APIRouter(prefix="/eval", tags=["eval"])


@router.post("/runs", response_model=EvalRunOut, status_code=status.HTTP_202_ACCEPTED)
async def create_eval_run(
    request: EvalRunCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> EvalRunOut:
    run = EvalRun(
        suite_version=request.suite_version,
        generation_model=request.generation_model or "pending",
        judge_model=request.judge_model or "pending",
        retrieval_strategy=request.retrieval_strategy,
        status=EvalRunStatus.RUNNING,
        total_cases=0,
        thresholds_json={},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)
    background_tasks.add_task(_run_eval_in_background, run.id, request.model_dump())
    return _to_eval_run_out(run)


@router.get("/runs", response_model=Paginated[EvalRunOut])
async def list_eval_runs(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    status_filter: Annotated[EvalRunStatus | None, Query(alias="status")] = None,
) -> Paginated[EvalRunOut]:
    filters = []
    if status_filter is not None:
        filters.append(EvalRun.status == status_filter)

    total = await db.scalar(select(func.count()).select_from(EvalRun).where(*filters))
    stmt = (
        select(EvalRun)
        .where(*filters)
        .order_by(EvalRun.started_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    runs = list((await db.scalars(stmt)).all())
    return Paginated[EvalRunOut](
        data=[_to_eval_run_out(run) for run in runs],
        meta=PageMeta(page=page, per_page=per_page, total=int(total or 0)),
    )


@router.get("/runs/{run_id}", response_model=EvalRunOut)
async def get_eval_run(run_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]) -> EvalRunOut:
    run = await db.get(EvalRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Eval run not found")
    return _to_eval_run_out(run)


@router.get("/runs/{run_id}/cases", response_model=Paginated[EvalCaseOut])
async def list_eval_cases(
    run_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=200)] = 50,
    passed: Annotated[bool | None, Query()] = None,
) -> Paginated[EvalCaseOut]:
    filters = [EvalCase.run_id == run_id]
    if passed is not None:
        filters.append(EvalCase.passed == passed)

    total = await db.scalar(select(func.count()).select_from(EvalCase).where(*filters))
    stmt = (
        select(EvalCase)
        .where(*filters)
        .order_by(EvalCase.created_at.asc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    rows = list((await db.scalars(stmt)).all())
    return Paginated[EvalCaseOut](
        data=[_to_eval_case_out(row) for row in rows],
        meta=PageMeta(page=page, per_page=per_page, total=int(total or 0)),
    )


async def _run_eval_in_background(run_id: uuid.UUID, payload: dict) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        await run_eval_suite(session=session, request=EvalRunCreate.model_validate(payload), run_id=run_id)


def _to_eval_run_out(run: EvalRun) -> EvalRunOut:
    return EvalRunOut(
        id=run.id,
        suite_version=run.suite_version,
        git_sha=run.git_sha,
        generation_model=run.generation_model,
        judge_model=run.judge_model,
        retrieval_strategy=run.retrieval_strategy,
        status=run.status.value,
        total_cases=run.total_cases,
        cases_passed=run.cases_passed,
        faithfulness_mean=run.faithfulness_mean,
        context_precision_mean=run.context_precision_mean,
        context_recall_mean=run.context_recall_mean,
        answer_relevancy_mean=run.answer_relevancy_mean,
        thresholds_json=run.thresholds_json,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _to_eval_case_out(case: EvalCase) -> EvalCaseOut:
    return EvalCaseOut(
        id=case.id,
        fixture_case_id=case.fixture_case_id,
        question=case.question,
        ground_truth=case.ground_truth,
        generated_answer=case.generated_answer,
        contexts_json=case.contexts_json,
        faithfulness=case.faithfulness,
        context_precision=case.context_precision,
        context_recall=case.context_recall,
        answer_relevancy=case.answer_relevancy,
        passed=case.passed,
        created_at=case.created_at,
    )
