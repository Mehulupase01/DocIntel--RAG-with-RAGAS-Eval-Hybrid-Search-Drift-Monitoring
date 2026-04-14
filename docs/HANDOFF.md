# Handoff

## Current Status
- Active phase: Phase 7 - Drift Monitoring
- Phase 6 objective: add structured request tracing, Prometheus collectors, and optional LangSmith bootstrap without changing the existing API contracts
- Phase 6 delivered:
  - monitoring services for LangSmith setup, Prometheus collectors, and tracing middleware
  - explicit root `GET /metrics` route matching the blueprint contract
  - instrumentation hooks for retrieval score observations, LLM token/cost totals, and eval score gauges
  - observability docs plus metrics/tracing tests
- Phase 6 verified:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_metrics.py tests/test_tracing_middleware.py -v` (`2 passed`)
  - full regression sweep through implemented Phases 1-6: `29 passed`
  - in-process `POST /api/v1/search` followed by `GET /metrics` returned non-zero request counters for the search path
- Residual environment note: Windows host access to `localhost:8000` remains flaky, so current-phase route verification used in-process ASGI calls per the user's updated execution policy
- Runtime note: per user direction on 2026-04-14, OpenRouter-backed live `/api/v1/answer` verification is deferred to the final deployment/hardening gate rather than blocking Phase 4 closure
- Runtime note: per the same execution policy, live OpenRouter-backed eval runs and the GitHub Actions PR gate remain deferred to the final deployment/hardening gate rather than blocking Phase 5 closure
- Runtime note: LangSmith remains env-gated and was not live-verified because `LANGSMITH_API_KEY` is optional and not required for intermediate phase closure

## Next Step
- Execute Phase 7 from the blueprint only:
  - add drift report model, schema, migration `005`, and report persistence
  - implement the one-shot drift runner, report writer, and drift endpoints
  - add scheduler scaffolding for the weekly job while keeping the app startup stable
  - verify seeded drift computations and artifact output locally, then commit and push
- Runtime gate for final deployment verification:
  - real OpenRouter-backed `/api/v1/answer`, eval runs, the PR workflow secret-backed execution, and optional LangSmith tracing remain deferred until the final live verification pass
