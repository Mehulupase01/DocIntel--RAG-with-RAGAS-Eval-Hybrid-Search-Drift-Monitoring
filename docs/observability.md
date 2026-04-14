# Observability

## Metrics
- `docintel_requests_total`
- `docintel_request_duration_seconds`
- `docintel_retrieval_score`
- `docintel_llm_tokens_total`
- `docintel_llm_cost_usd_total`
- `docintel_eval_score`

## Middleware
- Every request gets an `X-Request-ID` if the caller did not supply one.
- Request completion is structured-logged with method, path, status code, and latency.
- Prometheus request counters and duration histograms are updated by the tracing middleware.

## LangSmith
- LangSmith remains optional.
- If `LANGSMITH_API_KEY` is set and `LANGSMITH_TRACING=true`, startup enables LangSmith environment variables for downstream tracing integrations.
