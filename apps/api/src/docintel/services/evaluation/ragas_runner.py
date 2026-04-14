from __future__ import annotations

import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Protocol, cast

from langchain_openai import ChatOpenAI
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset, EvaluationResult
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config import get_settings
from docintel.models.eval_case import EvalCase
from docintel.models.eval_run import EvalRun, EvalRunStatus
from docintel.schemas.answer import AnswerRequest
from docintel.schemas.eval import EvalRunCreate
from docintel.services.evaluation.fixture_loader import FixtureSuite, load_fixture
from docintel.services.evaluation.thresholds import EvalScores, EvalThresholds, case_passes, get_eval_thresholds
from docintel.services.generation.answerer import AnswerResult, answer_question
from docintel.services.generation.llm_client import LLMProviderNotConfiguredError
from docintel.services.monitoring.metrics import record_eval_scores


class EvalScorer(Protocol):
    async def score(
        self,
        *,
        question: str,
        ground_truth: str,
        generated_answer: str,
        contexts: list[str],
    ) -> EvalScores: ...


class AnswerGenerator(Protocol):
    async def __call__(
        self,
        *,
        session: AsyncSession,
        request: AnswerRequest,
    ) -> AnswerResult: ...


@dataclass(slots=True)
class EvalRunResult:
    run_id: uuid.UUID
    status: EvalRunStatus
    total_cases: int
    cases_passed: int
    faithfulness_mean: float | None
    context_precision_mean: float | None
    context_recall_mean: float | None
    answer_relevancy_mean: float | None


class RagasJudgeScorer:
    def __init__(self, judge_model: str) -> None:
        settings = get_settings()
        if not settings.openrouter_api_key:
            raise LLMProviderNotConfiguredError("OPENROUTER_API_KEY is not configured")

        chat_model = ChatOpenAI(
            model=judge_model,
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            temperature=0.0,
            max_retries=2,
        )
        self._llm = LangchainLLMWrapper(chat_model)

    async def score(
        self,
        *,
        question: str,
        ground_truth: str,
        generated_answer: str,
        contexts: list[str],
    ) -> EvalScores:
        dataset = EvaluationDataset.from_list(
            [
                {
                    "user_input": question,
                    "response": generated_answer,
                    "reference": ground_truth,
                    "retrieved_contexts": contexts,
                }
            ]
        )
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, context_precision, context_recall, answer_relevancy],
            llm=self._llm,
            raise_exceptions=True,
            show_progress=False,
            return_executor=False,
        )
        result = cast(EvaluationResult, result)
        row = result.scores[0]
        return EvalScores(
            faithfulness=float(row["faithfulness"]),
            context_precision=float(row["context_precision"]),
            context_recall=float(row["context_recall"]),
            answer_relevancy=float(row["answer_relevancy"]),
        )


async def run_eval_suite(
    *,
    session: AsyncSession,
    request: EvalRunCreate,
    fixture: FixtureSuite | None = None,
    scorer: EvalScorer | None = None,
    answer_generator: AnswerGenerator | None = None,
    run_id: uuid.UUID | None = None,
) -> EvalRunResult:
    settings = get_settings()
    thresholds = get_eval_thresholds(settings)
    fixture_suite = fixture or load_fixture(suite_version=request.suite_version)
    generation_model = request.generation_model or settings.default_generation_model
    judge_model = request.judge_model or settings.default_judge_model

    run = await _get_or_create_run(
        session=session,
        request=request,
        thresholds=thresholds,
        total_cases=len(fixture_suite.cases),
        generation_model=generation_model,
        judge_model=judge_model,
        run_id=run_id,
    )
    scorer_impl = scorer or RagasJudgeScorer(judge_model)
    answer_impl = answer_generator or answer_question

    score_rows: list[EvalScores] = []
    passed_count = 0

    try:
        for case in fixture_suite.cases:
            answer_result = await answer_impl(
                session=session,
                request=AnswerRequest(
                    query=case.question,
                    top_k=8,
                    strategy=request.retrieval_strategy,
                    model=generation_model,
                ),
            )
            contexts = [context.text for context in answer_result.contexts]
            scores = await scorer_impl.score(
                question=case.question,
                ground_truth=case.ground_truth,
                generated_answer=answer_result.answer,
                contexts=contexts,
            )
            passed = case_passes(scores, thresholds)
            passed_count += int(passed)
            score_rows.append(scores)

            session.add(
                EvalCase(
                    run_id=run.id,
                    fixture_case_id=case.id,
                    question=case.question,
                    ground_truth=case.ground_truth,
                    generated_answer=answer_result.answer,
                    contexts_json=contexts,
                    faithfulness=scores.faithfulness,
                    context_precision=scores.context_precision,
                    context_recall=scores.context_recall,
                    answer_relevancy=scores.answer_relevancy,
                    passed=passed,
                )
            )
            await session.flush()

            if request.fail_fast and not passed:
                break

        run.total_cases = len(fixture_suite.cases)
        run.cases_passed = passed_count
        run.faithfulness_mean = _mean_or_none(score_rows, "faithfulness")
        run.context_precision_mean = _mean_or_none(score_rows, "context_precision")
        run.context_recall_mean = _mean_or_none(score_rows, "context_recall")
        run.answer_relevancy_mean = _mean_or_none(score_rows, "answer_relevancy")
        record_eval_scores(
            run.faithfulness_mean,
            run.context_precision_mean,
            run.context_recall_mean,
            run.answer_relevancy_mean,
        )
        run.status = (
            EvalRunStatus.PASSED
            if passed_count == len(score_rows) and len(score_rows) == len(fixture_suite.cases)
            else EvalRunStatus.FAILED
        )
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
    except Exception:
        run.status = EvalRunStatus.ERRORED
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()
        raise

    return EvalRunResult(
        run_id=run.id,
        status=run.status,
        total_cases=run.total_cases,
        cases_passed=run.cases_passed,
        faithfulness_mean=run.faithfulness_mean,
        context_precision_mean=run.context_precision_mean,
        context_recall_mean=run.context_recall_mean,
        answer_relevancy_mean=run.answer_relevancy_mean,
    )


async def _get_or_create_run(
    *,
    session: AsyncSession,
    request: EvalRunCreate,
    thresholds: EvalThresholds,
    total_cases: int,
    generation_model: str,
    judge_model: str,
    run_id: uuid.UUID | None,
) -> EvalRun:
    if run_id is not None:
        run = await session.get(EvalRun, run_id)
        if run is None:
            raise ValueError(f"Eval run {run_id} does not exist")
        run.generation_model = generation_model
        run.judge_model = judge_model
        run.thresholds_json = thresholds.as_json()
        return run

    run = EvalRun(
        suite_version=request.suite_version,
        git_sha=_current_git_sha(),
        generation_model=generation_model,
        judge_model=judge_model,
        retrieval_strategy=request.retrieval_strategy,
        status=EvalRunStatus.RUNNING,
        total_cases=total_cases,
        thresholds_json=thresholds.as_json(),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


def _mean_or_none(rows: list[EvalScores], field_name: str) -> float | None:
    if not rows:
        return None
    return float(mean(getattr(row, field_name) for row in rows))


def _current_git_sha() -> str | None:
    try:
        return (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            or None
        )
    except Exception:
        return None
