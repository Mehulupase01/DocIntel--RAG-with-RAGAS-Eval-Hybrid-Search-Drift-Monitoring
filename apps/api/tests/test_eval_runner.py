from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest
from docintel.models.eval_case import EvalCase
from docintel.models.eval_run import EvalRun, EvalRunStatus
from docintel.schemas.eval import EvalRunCreate
from docintel.schemas.search import RetrievedChunk
from docintel.services.evaluation import ci_gate
from docintel.services.evaluation.fixture_loader import FixtureSuite, FixtureValidationError, load_fixture
from docintel.services.evaluation.ragas_runner import EvalRunResult, run_eval_suite
from docintel.services.evaluation.thresholds import EvalScores
from docintel.services.generation.answerer import AnswerResult
from sqlalchemy import func, select


def _fixture_suite() -> FixtureSuite:
    from docintel.services.evaluation.fixture_loader import FixtureCase

    return FixtureSuite(
        version="v0.1",
        source_doc_sha256="sha",
        cases=[
            FixtureCase(
                id="case-001",
                question="What is a high-risk AI system?",
                ground_truth="A high-risk AI system falls under Article 6 and Annex III.",
                expected_articles=["Article 6", "Annex III"],
                category="definitions",
            ),
            FixtureCase(
                id="case-002",
                question="What are prohibited AI practices?",
                ground_truth="Article 5 prohibits certain manipulative, exploitative, and social-scoring practices.",
                expected_articles=["Article 5"],
                category="prohibited_practices",
            ),
            FixtureCase(
                id="case-003",
                question="What does Article 14 require?",
                ground_truth="Article 14 requires effective human oversight for high-risk AI systems.",
                expected_articles=["Article 14"],
                category="human_oversight",
            ),
        ],
    )


def _context(text: str, section_path: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="EU AI Act",
        ordinal=1,
        text=text,
        section_path=section_path,
        page_start=1,
        page_end=1,
        rank=1,
        bm25_score=0.8,
        vector_score=0.7,
        fused_score=0.9,
        rerank_score=0.95,
    )


class _StubScorer:
    def __init__(self, mapping: dict[str, EvalScores]) -> None:
        self.mapping = mapping

    async def score(self, *, question: str, ground_truth: str, generated_answer: str, contexts: list[str]) -> EvalScores:
        return self.mapping[question]


async def _stub_answer_generator(*, session, request):
    context_map = {
        "What is a high-risk AI system?": [_context("Article 6 defines high-risk AI systems by reference to Annex III.", "Article 6")],
        "What are prohibited AI practices?": [_context("Article 5 prohibits certain AI practices.", "Article 5")],
        "What does Article 14 require?": [_context("Article 14 requires human oversight.", "Article 14")],
    }
    answer_map = {
        "What is a high-risk AI system?": "A high-risk AI system is defined by Article 6 and Annex III.",
        "What are prohibited AI practices?": "Article 5 prohibits certain manipulative and social-scoring practices.",
        "What does Article 14 require?": "Article 14 requires human oversight over high-risk AI systems.",
    }
    return AnswerResult(
        query_id=uuid.uuid4(),
        answer_id=uuid.uuid4(),
        answer=answer_map[request.query],
        citations=[],
        contexts=context_map[request.query],
        model=request.model or "stub-model",
        prompt_tokens=10,
        completion_tokens=10,
        cost_usd=0.0,
        latency_ms=10,
    )


def test_fixture_loader_validates_schema(tmp_path: Path):
    fixture = load_fixture()
    assert fixture.version == "v0.1"
    assert len(fixture.cases) == 25

    invalid_fixture_path = tmp_path / "invalid_fixture.json"
    invalid_fixture_path.write_text(json.dumps({"version": "v0.1", "source_doc_sha256": "x" * 64}), encoding="utf-8")

    with pytest.raises(FixtureValidationError):
        load_fixture(fixture_path=invalid_fixture_path)


@pytest.mark.asyncio
async def test_ragas_runner_persists_run_and_cases_with_stubbed_judge(postgres_db_session):
    scores = {
        "What is a high-risk AI system?": EvalScores(0.95, 0.95, 0.95, 0.95),
        "What are prohibited AI practices?": EvalScores(0.91, 0.92, 0.93, 0.94),
        "What does Article 14 require?": EvalScores(0.70, 0.90, 0.90, 0.90),
    }

    result = await run_eval_suite(
        session=postgres_db_session,
        request=EvalRunCreate(),
        fixture=_fixture_suite(),
        scorer=_StubScorer(scores),
        answer_generator=_stub_answer_generator,
    )

    run = await postgres_db_session.scalar(select(EvalRun).where(EvalRun.id == result.run_id))
    case_count = await postgres_db_session.scalar(select(func.count(EvalCase.id)))

    assert run is not None
    assert run.status == EvalRunStatus.FAILED
    assert run.total_cases == 3
    assert run.cases_passed == 2
    assert case_count == 3
    assert run.faithfulness_mean is not None


@pytest.mark.asyncio
async def test_eval_endpoints_pagination(postgres_client, postgres_db_session):
    run_one = EvalRun(
        suite_version="v1",
        git_sha="a" * 40,
        generation_model="gen-1",
        judge_model="judge-1",
        retrieval_strategy="hybrid_reranked",
        status=EvalRunStatus.PASSED,
        total_cases=2,
        cases_passed=2,
        thresholds_json={"faithfulness": 0.85},
    )
    run_two = EvalRun(
        suite_version="v1",
        git_sha="b" * 40,
        generation_model="gen-2",
        judge_model="judge-2",
        retrieval_strategy="hybrid_reranked",
        status=EvalRunStatus.FAILED,
        total_cases=1,
        cases_passed=0,
        thresholds_json={"faithfulness": 0.85},
    )
    postgres_db_session.add_all([run_one, run_two])
    await postgres_db_session.flush()
    postgres_db_session.add_all(
        [
            EvalCase(
                run_id=run_one.id,
                fixture_case_id="case-1",
                question="Q1",
                ground_truth="G1",
                generated_answer="A1",
                contexts_json=["C1"],
                faithfulness=0.9,
                context_precision=0.9,
                context_recall=0.9,
                answer_relevancy=0.9,
                passed=True,
            ),
            EvalCase(
                run_id=run_one.id,
                fixture_case_id="case-2",
                question="Q2",
                ground_truth="G2",
                generated_answer="A2",
                contexts_json=["C2"],
                faithfulness=0.9,
                context_precision=0.9,
                context_recall=0.9,
                answer_relevancy=0.9,
                passed=False,
            ),
        ]
    )
    await postgres_db_session.commit()

    runs_response = await postgres_client.get("/api/v1/eval/runs?page=1&per_page=1")
    assert runs_response.status_code == 200
    assert runs_response.json()["meta"]["total"] == 2
    assert len(runs_response.json()["data"]) == 1

    cases_response = await postgres_client.get(f"/api/v1/eval/runs/{run_one.id}/cases?passed=true")
    assert cases_response.status_code == 200
    assert cases_response.json()["meta"]["total"] == 1
    assert cases_response.json()["data"][0]["passed"] is True


@pytest.mark.asyncio
async def test_ci_gate_exits_nonzero_on_threshold_breach(monkeypatch):
    async def _stub_run_eval_suite(*, session, request):
        return EvalRunResult(
            run_id=uuid.uuid4(),
            status=EvalRunStatus.FAILED,
            total_cases=3,
            cases_passed=2,
            faithfulness_mean=0.8,
            context_precision_mean=0.8,
            context_recall_mean=0.8,
            answer_relevancy_mean=0.8,
        )

    monkeypatch.setattr(ci_gate, "run_eval_suite", _stub_run_eval_suite)
    monkeypatch.setattr(sys, "argv", ["ci_gate", "--fail-on-breach"])

    exit_code = await ci_gate._main()
    assert exit_code == 1
