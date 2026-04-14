# Handoff

## Current Status
- Active phase: Phase 8 - Streamlit Dashboard
- Phase 7 objective: add persisted Evidently drift reporting, a one-shot CLI, browsable drift endpoints, and an in-process APScheduler weekly job
- Phase 7 delivered:
  - `drift_reports` model, schema, and migration `005_drift_reports`
  - Evidently-powered drift runner with query embeddings, query/retrieval feature drift, and persisted HTML artifacts
  - `/api/v1/drift/reports` create/list/detail endpoints plus `python -m docintel.tools.run_drift`
  - APScheduler startup wiring for the weekly `weekly-drift-report` job
  - drift docs plus seeded Postgres-backed endpoint/runner tests
- Phase 7 verified:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_drift_runner.py -v` (`4 passed`)
  - `uv run python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7`
  - ASGI `GET /api/v1/drift/reports`
  - app lifespan startup logged the registered `weekly-drift-report` scheduler job
  - full regression sweep through implemented Phases 1-7: `33 passed`
- Residual environment note: Windows host access to `localhost:8000` remains flaky, so current-phase route verification used in-process ASGI calls per the user's updated execution policy
- Runtime note: per user direction on 2026-04-14, OpenRouter-backed live `/api/v1/answer` verification is deferred to the final deployment/hardening gate rather than blocking Phase 4 closure
- Runtime note: per the same execution policy, live OpenRouter-backed eval runs and the GitHub Actions PR gate remain deferred to the final deployment/hardening gate rather than blocking Phase 5 closure
- Runtime note: LangSmith remains env-gated and was not live-verified because `LANGSMITH_API_KEY` is optional and not required for intermediate phase closure
- Runtime note: the local `docintel` database had no prior reference-window query traffic, so Phase 7 verification seeded deterministic historical query/retrieval windows in the local DB before the one-shot drift CLI was run

## Next Step
- Execute Phase 8 from the blueprint only:
  - scaffold `apps/dashboard` with Streamlit, Plotly, and the read-only Postgres/API helpers
  - build the home view plus the four dashboard pages for eval trends, drift reports, cost/latency, and retrieval exploration
  - add the dashboard Dockerfile and `ops/docker/compose.full.yml`
  - verify the dashboard pages against the seeded local dataset, then commit and push
- Runtime gate for final deployment verification:
  - real OpenRouter-backed `/api/v1/answer`, eval runs, the PR workflow secret-backed execution, and optional LangSmith tracing remain deferred until the final live verification pass
