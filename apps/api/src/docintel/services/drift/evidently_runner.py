from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Protocol

import pandas as pd
from evidently import ColumnMapping
from evidently.metrics import ColumnDriftMetric, DataDriftTable, DatasetDriftMetric, EmbeddingsDriftMetric
from evidently.metrics.data_drift.embedding_drift_methods import distance
from evidently.report import Report
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.config import Settings, get_settings
from docintel.models.drift_report import DriftStatus
from docintel.models.query import Query
from docintel.models.retrieval import Retrieval
from docintel.services.ingestion.embedder import get_embedder

FEATURE_COLUMNS = [
    "query_length_tokens",
    "retrieval_count",
    "rank_stability",
    "mean_rerank_score",
]
MIN_REPORT_ROWS = 31
EMBEDDING_NAME = "query_embedding"


class SupportsEmbedding(Protocol):
    def embed_texts(self, texts: list[str], batch_size: int = 16) -> list[list[float]]: ...


@dataclass(slots=True)
class DriftSample:
    query_id: str
    query_text: str
    query_length_tokens: int
    retrieval_count: int
    rank_stability: float
    mean_rerank_score: float


@dataclass(slots=True)
class DriftAnalysisResult:
    window_start: datetime
    window_end: datetime
    reference_window_start: datetime
    reference_window_end: datetime
    embedding_drift_score: float | None
    query_drift_score: float | None
    retrieval_quality_delta: float | None
    status: DriftStatus
    payload_json: dict
    html: str


async def run_drift_analysis(
    *,
    session: AsyncSession,
    window_days: int,
    reference_window_days: int,
    now: datetime | None = None,
    embedder: SupportsEmbedding | None = None,
    settings: Settings | None = None,
) -> DriftAnalysisResult:
    resolved_settings = settings or get_settings()
    current_end = now or datetime.now(timezone.utc)
    if current_end.tzinfo is None:
        current_end = current_end.replace(tzinfo=timezone.utc)
    current_start = current_end - timedelta(days=window_days)
    reference_end = current_start
    reference_start = reference_end - timedelta(days=reference_window_days)

    current_samples = await _load_window_samples(session, start=current_start, end=current_end)
    reference_samples = await _load_window_samples(session, start=reference_start, end=reference_end)
    if not current_samples or not reference_samples:
        raise ValueError("Drift analysis requires query traffic in both the current and reference windows")

    embedder_impl = embedder or get_embedder()
    current_frame = _build_frame(current_samples, embedder_impl)
    reference_frame = _build_frame(reference_samples, embedder_impl)
    report_current = _prepare_report_frame(current_frame)
    report_reference = _prepare_report_frame(reference_frame)

    report = _build_report(resolved_settings)
    report.run(
        reference_data=report_reference,
        current_data=report_current,
        column_mapping=_build_column_mapping(report_current),
    )
    report_json = report.as_dict()

    embedding_metric = _metric_result(report_json, "EmbeddingsDriftMetric", embeddings_name=EMBEDDING_NAME)
    dataset_metric = _metric_result(report_json, "DatasetDriftMetric")
    rank_metric = _metric_result(report_json, "ColumnDriftMetric", column_name="rank_stability")
    rerank_metric = _metric_result(report_json, "ColumnDriftMetric", column_name="mean_rerank_score")

    embedding_drift_score = _float_or_none(embedding_metric.get("drift_score"))
    query_drift_score = _float_or_none(dataset_metric.get("share_of_drifted_columns"))
    retrieval_quality_delta = _mean_delta(reference_frame, current_frame, "mean_rerank_score")
    rank_stability_delta = _mean_delta(reference_frame, current_frame, "rank_stability")

    status_score = max(
        embedding_drift_score or 0.0,
        query_drift_score or 0.0,
        abs(retrieval_quality_delta or 0.0),
        abs(rank_stability_delta or 0.0),
    )
    status = resolve_drift_status(
        score=status_score,
        warning_threshold=resolved_settings.drift_warning_threshold,
        alert_threshold=resolved_settings.drift_alert_threshold,
    )

    payload_json = {
        "summary": {
            "current_query_count": int(len(current_frame)),
            "reference_query_count": int(len(reference_frame)),
            "report_row_count_current": int(len(report_current)),
            "report_row_count_reference": int(len(report_reference)),
            "status_score": status_score,
            "warning_threshold": resolved_settings.drift_warning_threshold,
            "alert_threshold": resolved_settings.drift_alert_threshold,
        },
        "metrics": {
            "embedding_drift": embedding_metric,
            "query_feature_drift": dataset_metric,
            "rank_stability": {
                **rank_metric,
                "reference_mean": _column_mean(reference_frame, "rank_stability"),
                "current_mean": _column_mean(current_frame, "rank_stability"),
                "delta": rank_stability_delta,
            },
            "mean_rerank_score": {
                **rerank_metric,
                "reference_mean": _column_mean(reference_frame, "mean_rerank_score"),
                "current_mean": _column_mean(current_frame, "mean_rerank_score"),
                "delta": retrieval_quality_delta,
            },
        },
        "report_json": report_json,
    }

    return DriftAnalysisResult(
        window_start=current_start,
        window_end=current_end,
        reference_window_start=reference_start,
        reference_window_end=reference_end,
        embedding_drift_score=embedding_drift_score,
        query_drift_score=query_drift_score,
        retrieval_quality_delta=retrieval_quality_delta,
        status=status,
        payload_json=payload_json,
        html=report.get_html(),
    )


def resolve_drift_status(*, score: float, warning_threshold: float, alert_threshold: float) -> DriftStatus:
    if score >= alert_threshold:
        return DriftStatus.ALERT
    if score >= warning_threshold:
        return DriftStatus.WARNING
    return DriftStatus.OK


def _build_report(settings: Settings) -> Report:
    return Report(
        metrics=[
            EmbeddingsDriftMetric(
                EMBEDDING_NAME,
                drift_method=distance(
                    dist="cosine",
                    threshold=settings.drift_warning_threshold,
                ),
            ),
            DatasetDriftMetric(columns=FEATURE_COLUMNS),
            ColumnDriftMetric("rank_stability"),
            ColumnDriftMetric("mean_rerank_score"),
            DataDriftTable(columns=FEATURE_COLUMNS),
        ]
    )


def _build_column_mapping(frame: pd.DataFrame) -> ColumnMapping:
    embedding_columns = [column for column in frame.columns if column.startswith("embedding_")]
    return ColumnMapping(
        numerical_features=FEATURE_COLUMNS,
        embeddings={EMBEDDING_NAME: embedding_columns},
    )


def _ensure_min_report_rows(frame: pd.DataFrame) -> pd.DataFrame:
    if len(frame) >= MIN_REPORT_ROWS:
        return frame
    missing_rows = MIN_REPORT_ROWS - len(frame)
    filler = frame.sample(n=missing_rows, replace=True, random_state=42)
    return pd.concat([frame, filler], ignore_index=True)


def _prepare_report_frame(frame: pd.DataFrame) -> pd.DataFrame:
    prepared = _ensure_min_report_rows(frame).copy()
    embedding_columns = [column for column in prepared.columns if column.startswith("embedding_")]
    for column_index, column_name in enumerate(embedding_columns, start=1):
        prepared[column_name] = prepared[column_name].astype(float) + (
            prepared.index.to_series().add(1).mul(column_index).mul(1e-9)
        )
    return prepared


def _build_frame(samples: list[DriftSample], embedder: SupportsEmbedding) -> pd.DataFrame:
    embeddings = embedder.embed_texts([sample.query_text for sample in samples])
    if not embeddings:
        raise ValueError("Drift analysis requires at least one embedded query")

    dimension = len(embeddings[0])
    rows = []
    for sample, embedding in zip(samples, embeddings, strict=True):
        row = {
            "query_length_tokens": sample.query_length_tokens,
            "retrieval_count": sample.retrieval_count,
            "rank_stability": sample.rank_stability,
            "mean_rerank_score": sample.mean_rerank_score,
        }
        row.update({f"embedding_{index}": value for index, value in enumerate(embedding[:dimension])})
        rows.append(row)
    return pd.DataFrame(rows)


async def _load_window_samples(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
) -> list[DriftSample]:
    stmt = (
        select(Query, Retrieval)
        .outerjoin(Retrieval, Retrieval.query_id == Query.id)
        .where(Query.created_at >= start, Query.created_at < end)
        .order_by(Query.created_at.asc(), Query.id.asc(), Retrieval.rank.asc())
    )
    rows = (await session.execute(stmt)).all()

    grouped: dict[str, dict[str, object]] = {}
    for query, retrieval in rows:
        bucket = grouped.setdefault(
            str(query.id),
            {
                "query": query,
                "retrievals": [],
            },
        )
        if retrieval is not None:
            bucket["retrievals"].append(retrieval)

    return [
        DriftSample(
            query_id=query_id,
            query_text=bucket["query"].query_text,
            query_length_tokens=len(bucket["query"].query_text.split()),
            retrieval_count=len(bucket["retrievals"]),
            rank_stability=_compute_rank_stability(bucket["retrievals"]),
            mean_rerank_score=_compute_mean_rerank_score(bucket["retrievals"]),
        )
        for query_id, bucket in grouped.items()
    ]


def _compute_mean_rerank_score(retrievals: list[Retrieval]) -> float:
    values = [float(retrieval.rerank_score) for retrieval in retrievals if retrieval.rerank_score is not None]
    if not values:
        return 0.0
    return float(mean(values))


def _compute_rank_stability(retrievals: list[Retrieval]) -> float:
    if len(retrievals) < 2:
        return 1.0

    final_ranked = sorted(retrievals, key=lambda item: item.rank)
    fused_ranked = sorted(
        retrievals,
        key=lambda item: (
            -(item.fused_score if item.fused_score is not None else float("-inf")),
            item.rank,
        ),
    )
    fused_rank_by_chunk = {retrieval.chunk_id: index for index, retrieval in enumerate(fused_ranked, start=1)}
    n = len(final_ranked)
    squared_deltas = [
        (position - fused_rank_by_chunk[retrieval.chunk_id]) ** 2
        for position, retrieval in enumerate(final_ranked, start=1)
    ]
    rho = 1.0 - (6.0 * sum(squared_deltas)) / (n * (n**2 - 1))
    return max(0.0, min(1.0, (rho + 1.0) / 2.0))


def _metric_result(report_json: dict, metric_name: str, column_name: str | None = None, embeddings_name: str | None = None) -> dict:
    for metric in report_json.get("metrics", []):
        if metric.get("metric") != metric_name:
            continue
        result = metric.get("result", {})
        if column_name is not None and result.get("column_name") != column_name:
            continue
        if embeddings_name is not None and result.get("embeddings_name") != embeddings_name:
            continue
        return result
    return {}


def _mean_delta(reference_frame: pd.DataFrame, current_frame: pd.DataFrame, column_name: str) -> float | None:
    reference_mean = _column_mean(reference_frame, column_name)
    current_mean = _column_mean(current_frame, column_name)
    if reference_mean is None or current_mean is None:
        return None
    return current_mean - reference_mean


def _column_mean(frame: pd.DataFrame, column_name: str) -> float | None:
    if frame.empty:
        return None
    return float(frame[column_name].mean())


def _float_or_none(value) -> float | None:
    if value is None:
        return None
    return float(value)
