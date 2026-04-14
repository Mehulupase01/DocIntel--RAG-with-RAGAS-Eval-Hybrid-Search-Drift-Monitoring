from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.db import (
    answers,
    dashboard_metadata,
    drift_reports,
    eval_runs,
    fetch_daily_costs,
    fetch_drift_reports,
    fetch_eval_trends,
    fetch_home_kpis,
    fetch_latency_summary,
    fetch_model_cost_breakdown,
    queries,
)
from sqlalchemy import create_engine


def _seed_dashboard_fixture(engine) -> datetime:
    now = datetime(2026, 4, 14, 12, 0, tzinfo=timezone.utc)
    dashboard_metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            eval_runs.insert(),
            [
                {
                    "id": "eval-1",
                    "suite_version": "v1",
                    "generation_model": "anthropic/claude-haiku-4-5",
                    "judge_model": "openai/gpt-4o-mini",
                    "retrieval_strategy": "hybrid_reranked",
                    "status": "passed",
                    "total_cases": 25,
                    "cases_passed": 24,
                    "faithfulness_mean": 0.91,
                    "context_precision_mean": 0.90,
                    "context_recall_mean": 0.86,
                    "answer_relevancy_mean": 0.89,
                    "thresholds_json": {},
                    "started_at": now - timedelta(days=2),
                    "finished_at": now - timedelta(days=2, minutes=-5),
                },
                {
                    "id": "eval-2",
                    "suite_version": "v1",
                    "generation_model": "anthropic/claude-haiku-4-5",
                    "judge_model": "openai/gpt-4o-mini",
                    "retrieval_strategy": "hybrid_reranked",
                    "status": "passed",
                    "total_cases": 25,
                    "cases_passed": 25,
                    "faithfulness_mean": 0.93,
                    "context_precision_mean": 0.92,
                    "context_recall_mean": 0.88,
                    "answer_relevancy_mean": 0.91,
                    "thresholds_json": {},
                    "started_at": now - timedelta(days=1),
                    "finished_at": now - timedelta(days=1, minutes=-5),
                },
            ],
        )
        connection.execute(
            drift_reports.insert(),
            [
                {
                    "id": "drift-1",
                    "window_start": now - timedelta(days=7),
                    "window_end": now,
                    "reference_window_start": now - timedelta(days=14),
                    "reference_window_end": now - timedelta(days=7),
                    "embedding_drift_score": 0.10,
                    "query_drift_score": 0.20,
                    "retrieval_quality_delta": -0.18,
                    "status": "warning",
                    "html_path": str(Path("artifacts") / "drift-1.html"),
                    "payload_json": {"summary": {"status_score": 0.20}},
                    "created_at": now - timedelta(hours=6),
                }
            ],
        )
        connection.execute(
            queries.insert(),
            [
                {
                    "id": "query-search-1",
                    "strategy": "hybrid_reranked",
                    "latency_ms": 180,
                    "created_at": now - timedelta(days=1, hours=4),
                },
                {
                    "id": "query-search-2",
                    "strategy": "hybrid_reranked",
                    "latency_ms": 240,
                    "created_at": now - timedelta(days=1, hours=1),
                },
                {
                    "id": "query-answer-1",
                    "strategy": "hybrid_reranked",
                    "latency_ms": 205,
                    "created_at": now - timedelta(hours=12),
                },
            ],
        )
        connection.execute(
            answers.insert(),
            [
                {
                    "id": "answer-1",
                    "query_id": "query-answer-1",
                    "model": "anthropic/claude-haiku-4-5",
                    "cost_usd": 0.0125,
                    "latency_ms": 1320,
                    "created_at": now - timedelta(hours=12),
                },
                {
                    "id": "answer-2",
                    "query_id": "query-answer-2",
                    "model": "anthropic/claude-haiku-4-5",
                    "cost_usd": 0.0100,
                    "latency_ms": 980,
                    "created_at": now - timedelta(days=3),
                },
                {
                    "id": "answer-3",
                    "query_id": "query-answer-3",
                    "model": "openai/gpt-4o-mini",
                    "cost_usd": 0.0040,
                    "latency_ms": 860,
                    "created_at": now - timedelta(days=5),
                },
            ],
        )
    return now


def test_fetch_home_kpis_returns_expected_values(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard.db'}", future=True)
    now = _seed_dashboard_fixture(engine)

    kpis = fetch_home_kpis(engine=engine, now=now)

    assert kpis["latest_faithfulness"] == 0.93
    assert kpis["latest_drift_status"] == "warning"
    assert round(kpis["total_cost_usd_7d"], 4) == 0.0265
    assert kpis["p95_answer_latency_ms_7d"] is not None


def test_fetch_eval_and_drift_frames_have_expected_shape(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard.db'}", future=True)
    _seed_dashboard_fixture(engine)

    eval_frame = fetch_eval_trends(engine=engine, limit=10)
    drift_frame = fetch_drift_reports(engine=engine, limit=10)

    assert list(eval_frame["faithfulness_mean"]) == [0.91, 0.93]
    assert drift_frame.iloc[0]["status"] == "warning"
    assert "payload_json" in drift_frame.columns


def test_cost_latency_and_model_helpers_return_expected_shapes(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dashboard.db'}", future=True)
    now = _seed_dashboard_fixture(engine)

    costs = fetch_daily_costs(engine=engine, days=30, now=now)
    latency = fetch_latency_summary(engine=engine, days=30, now=now)
    models = fetch_model_cost_breakdown(engine=engine, days=30, now=now)

    assert not costs.empty
    assert set(latency["endpoint"]) == {"/api/v1/search", "/api/v1/answer"}
    assert set(models["model"]) == {"anthropic/claude-haiku-4-5", "openai/gpt-4o-mini"}
