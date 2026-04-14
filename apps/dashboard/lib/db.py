from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import pandas as pd
from sqlalchemy import JSON, Column, DateTime, Float, Integer, MetaData, String, Table, create_engine, select
from sqlalchemy.engine import Engine

dashboard_metadata = MetaData()

eval_runs = Table(
    "eval_runs",
    dashboard_metadata,
    Column("id", String(64), primary_key=True),
    Column("suite_version", String(32)),
    Column("generation_model", String(128)),
    Column("judge_model", String(128)),
    Column("retrieval_strategy", String(64)),
    Column("status", String(32)),
    Column("total_cases", Integer),
    Column("cases_passed", Integer),
    Column("faithfulness_mean", Float),
    Column("context_precision_mean", Float),
    Column("context_recall_mean", Float),
    Column("answer_relevancy_mean", Float),
    Column("thresholds_json", JSON),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
)

drift_reports = Table(
    "drift_reports",
    dashboard_metadata,
    Column("id", String(64), primary_key=True),
    Column("window_start", DateTime(timezone=True)),
    Column("window_end", DateTime(timezone=True)),
    Column("reference_window_start", DateTime(timezone=True)),
    Column("reference_window_end", DateTime(timezone=True)),
    Column("embedding_drift_score", Float),
    Column("query_drift_score", Float),
    Column("retrieval_quality_delta", Float),
    Column("status", String(32)),
    Column("html_path", String(1024)),
    Column("payload_json", JSON),
    Column("created_at", DateTime(timezone=True)),
)

answers = Table(
    "answers",
    dashboard_metadata,
    Column("id", String(64), primary_key=True),
    Column("query_id", String(64)),
    Column("model", String(128)),
    Column("cost_usd", Float),
    Column("latency_ms", Integer),
    Column("created_at", DateTime(timezone=True)),
)

queries = Table(
    "queries",
    dashboard_metadata,
    Column("id", String(64), primary_key=True),
    Column("strategy", String(64)),
    Column("latency_ms", Integer),
    Column("created_at", DateTime(timezone=True)),
)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/docintel")
    return database_url.replace("+asyncpg", "+psycopg")


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_database_url(), future=True)


def fetch_home_kpis(*, engine: Engine | None = None, now: datetime | None = None) -> dict[str, float | str | None]:
    resolved_engine = engine or get_engine()
    resolved_now = now or datetime.now(timezone.utc)
    cutoff = resolved_now - timedelta(days=7)

    latest_eval = _fetch_frame(
        select(
            eval_runs.c.faithfulness_mean,
            eval_runs.c.started_at,
        )
        .order_by(eval_runs.c.started_at.desc())
        .limit(1),
        resolved_engine,
    )
    latest_drift = _fetch_frame(
        select(
            drift_reports.c.status,
            drift_reports.c.created_at,
        )
        .order_by(drift_reports.c.created_at.desc())
        .limit(1),
        resolved_engine,
    )
    recent_answers = _fetch_frame(
        select(answers.c.cost_usd, answers.c.latency_ms, answers.c.created_at).where(answers.c.created_at >= cutoff),
        resolved_engine,
    )

    latest_faithfulness = (
        float(latest_eval.iloc[0]["faithfulness_mean"]) if not latest_eval.empty else None
    )
    latest_drift_status = str(latest_drift.iloc[0]["status"]) if not latest_drift.empty else None
    total_cost = float(recent_answers["cost_usd"].fillna(0.0).sum()) if not recent_answers.empty else None
    p95_latency = _percentile(recent_answers["latency_ms"], 0.95) if not recent_answers.empty else None

    return {
        "latest_faithfulness": latest_faithfulness,
        "p95_answer_latency_ms_7d": p95_latency,
        "latest_drift_status": latest_drift_status,
        "total_cost_usd_7d": total_cost,
    }


def fetch_eval_trends(*, engine: Engine | None = None, limit: int = 100) -> pd.DataFrame:
    frame = _fetch_frame(
        select(
            eval_runs.c.started_at,
            eval_runs.c.status,
            eval_runs.c.retrieval_strategy,
            eval_runs.c.faithfulness_mean,
            eval_runs.c.context_precision_mean,
            eval_runs.c.context_recall_mean,
            eval_runs.c.answer_relevancy_mean,
            eval_runs.c.cases_passed,
            eval_runs.c.total_cases,
        )
        .order_by(eval_runs.c.started_at.desc())
        .limit(limit),
        engine or get_engine(),
    )
    if frame.empty:
        return frame
    frame["started_at"] = pd.to_datetime(frame["started_at"], utc=True)
    return frame.sort_values("started_at").reset_index(drop=True)


def fetch_drift_reports(*, engine: Engine | None = None, limit: int = 50) -> pd.DataFrame:
    frame = _fetch_frame(
        select(
            drift_reports.c.id,
            drift_reports.c.created_at,
            drift_reports.c.status,
            drift_reports.c.embedding_drift_score,
            drift_reports.c.query_drift_score,
            drift_reports.c.retrieval_quality_delta,
            drift_reports.c.html_path,
            drift_reports.c.payload_json,
        )
        .order_by(drift_reports.c.created_at.desc())
        .limit(limit),
        engine or get_engine(),
    )
    if frame.empty:
        return frame
    frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True)
    frame["id"] = frame["id"].astype(str)
    frame["html_path"] = frame["html_path"].astype(str)
    return frame.reset_index(drop=True)


def fetch_daily_costs(*, engine: Engine | None = None, days: int = 30, now: datetime | None = None) -> pd.DataFrame:
    resolved_engine = engine or get_engine()
    resolved_now = now or datetime.now(timezone.utc)
    cutoff = resolved_now - timedelta(days=days)
    frame = _fetch_frame(
        select(answers.c.created_at, answers.c.cost_usd).where(answers.c.created_at >= cutoff),
        resolved_engine,
    )
    if frame.empty:
        return pd.DataFrame(columns=["date", "cost_usd"])
    frame["created_at"] = pd.to_datetime(frame["created_at"], utc=True)
    frame["date"] = frame["created_at"].dt.date.astype(str)
    grouped = frame.groupby("date", as_index=False)["cost_usd"].sum()
    return grouped.sort_values("date").reset_index(drop=True)


def fetch_latency_summary(*, engine: Engine | None = None, days: int = 30, now: datetime | None = None) -> pd.DataFrame:
    resolved_engine = engine or get_engine()
    resolved_now = now or datetime.now(timezone.utc)
    cutoff = resolved_now - timedelta(days=days)

    search_frame = _fetch_frame(
        select(queries.c.latency_ms, queries.c.created_at)
        .select_from(queries.outerjoin(answers, answers.c.query_id == queries.c.id))
        .where(answers.c.id.is_(None), queries.c.created_at >= cutoff),
        resolved_engine,
    )
    answer_frame = _fetch_frame(
        select(answers.c.latency_ms, answers.c.created_at).where(answers.c.created_at >= cutoff),
        resolved_engine,
    )

    rows: list[dict[str, float | int | str]] = []
    for endpoint, frame in (("/api/v1/search", search_frame), ("/api/v1/answer", answer_frame)):
        if frame.empty:
            continue
        rows.append(
            {
                "endpoint": endpoint,
                "p50_latency_ms": _percentile(frame["latency_ms"], 0.50),
                "p95_latency_ms": _percentile(frame["latency_ms"], 0.95),
                "request_count": int(len(frame)),
            }
        )
    return pd.DataFrame(rows)


def fetch_model_cost_breakdown(
    *,
    engine: Engine | None = None,
    days: int = 30,
    now: datetime | None = None,
) -> pd.DataFrame:
    resolved_engine = engine or get_engine()
    resolved_now = now or datetime.now(timezone.utc)
    cutoff = resolved_now - timedelta(days=days)
    frame = _fetch_frame(
        select(answers.c.model, answers.c.cost_usd, answers.c.created_at).where(answers.c.created_at >= cutoff),
        resolved_engine,
    )
    if frame.empty:
        return pd.DataFrame(columns=["model", "cost_usd", "answer_count"])
    grouped = (
        frame.groupby("model", as_index=False)
        .agg(cost_usd=("cost_usd", "sum"), answer_count=("cost_usd", "count"))
        .sort_values("cost_usd", ascending=False)
        .reset_index(drop=True)
    )
    return grouped


def _fetch_frame(statement, engine: Engine) -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql(statement, connection)


def _percentile(series: pd.Series, quantile: float) -> float | None:
    if series.empty:
        return None
    return float(series.dropna().astype(float).quantile(quantile))
