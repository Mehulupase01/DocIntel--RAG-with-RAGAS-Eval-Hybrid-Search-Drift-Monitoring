from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram


REQUESTS_TOTAL = Counter(
    "docintel_requests_total",
    "Total HTTP requests handled by DocIntel.",
    labelnames=("method", "path", "status_code"),
)
REQUEST_DURATION_SECONDS = Histogram(
    "docintel_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "path"),
)
RETRIEVAL_SCORE = Histogram(
    "docintel_retrieval_score",
    "Observed retrieval score components.",
    labelnames=("strategy", "score_type"),
)
LLM_TOKENS_TOTAL = Counter(
    "docintel_llm_tokens_total",
    "Total LLM tokens used by DocIntel.",
    labelnames=("model", "token_type"),
)
LLM_COST_USD_TOTAL = Counter(
    "docintel_llm_cost_usd_total",
    "Total LLM cost observed by DocIntel in USD.",
    labelnames=("model",),
)
EVAL_SCORE = Gauge(
    "docintel_eval_score",
    "Latest aggregate evaluation score per metric.",
    labelnames=("metric",),
)


def record_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    REQUESTS_TOTAL.labels(method=method, path=path, status_code=str(status_code)).inc()
    REQUEST_DURATION_SECONDS.labels(method=method, path=path).observe(duration_seconds)


def record_retrieval_scores(strategy: str, results) -> None:
    for result in results:
        for score_type in ("bm25_score", "vector_score", "fused_score", "rerank_score"):
            value = getattr(result, score_type, None)
            if value is not None:
                RETRIEVAL_SCORE.labels(strategy=strategy, score_type=score_type).observe(float(value))


def record_llm_usage(model: str, prompt_tokens: int, completion_tokens: int, cost_usd: float) -> None:
    if prompt_tokens:
        LLM_TOKENS_TOTAL.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKENS_TOTAL.labels(model=model, token_type="completion").inc(completion_tokens)
    if cost_usd:
        LLM_COST_USD_TOTAL.labels(model=model).inc(cost_usd)


def record_eval_scores(
    faithfulness: float | None,
    context_precision: float | None,
    context_recall: float | None,
    answer_relevancy: float | None,
) -> None:
    metrics = {
        "faithfulness": faithfulness,
        "context_precision": context_precision,
        "context_recall": context_recall,
        "answer_relevancy": answer_relevancy,
    }
    for metric, value in metrics.items():
        if value is not None:
            EVAL_SCORE.labels(metric=metric).set(value)
