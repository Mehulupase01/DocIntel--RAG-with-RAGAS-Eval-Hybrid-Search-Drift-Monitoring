# Drift Monitoring

DocIntel compares the last `DRIFT_WINDOW_DAYS` of query and retrieval activity against the prior `DRIFT_REFERENCE_WINDOW_DAYS` using an Evidently report plus persisted summary scores.

## Compared Signals

- Query embedding drift: cosine distance between the mean embedding of current-window queries and the reference window.
- Query feature drift: Evidently dataset drift share across `query_length_tokens`, `retrieval_count`, `rank_stability`, and `mean_rerank_score`.
- Retrieval rank-stability: per-query Spearman stability between fused ranking and the final reranked order, normalized to `[0, 1]`.
- Mean rerank score delta: current-window mean rerank score minus the reference-window mean rerank score.

## Thresholds

- `warning`: aggregate drift score `>= 0.15`
- `alert`: aggregate drift score `>= 0.25`

The aggregate status score is the max of:

- `embedding_drift_score`
- `query_drift_score`
- `abs(retrieval_quality_delta)`
- `abs(rank_stability_delta)` from the report payload

## HTML Report Layout

Each generated report includes:

- an Evidently embeddings drift section for `query_embedding`
- per-column drift views for `rank_stability` and `mean_rerank_score`
- a dataset drift table for the query/retrieval feature set
- persisted JSON summary in `payload_json`
- saved HTML artifact at `ARTIFACT_STORAGE_PATH/drift/<report_id>.html`
