# Handoff

## Current Status
- Active phase: Phase 9 - Hardening
- Phase 8 objective: ship the Streamlit ops dashboard with KPI home, eval trends, drift reports, cost/latency, retrieval explorer, and the compose overlay
- Phase 8 delivered:
  - `apps/dashboard` project with pinned Streamlit, Plotly, pandas, SQLAlchemy, psycopg, and test support
  - read-only DB helper layer plus live `/search` API client wrapper
  - dashboard home plus all four blueprint pages
  - `apps/dashboard/Dockerfile`, `ops/docker/compose.full.yml`, and `docs/deployment.md`
  - dashboard DB-helper tests and Streamlit AppTest smoke coverage
- Phase 8 verified:
  - `uv sync` in `apps/dashboard`
  - `uv run pytest tests/test_db_queries.py -v` (`3 passed`)
  - `uv run python -m compileall app.py lib pages tests`
  - Streamlit `AppTest` rendered `app.py` plus all four page scripts successfully
  - `docker compose -f docker-compose.yml -f ops/docker/compose.full.yml config`
- Residual environment note: Windows host access to `localhost:8000` remains flaky, so current-phase route verification used in-process ASGI calls per the user's updated execution policy
- Runtime note: per user direction on 2026-04-14, OpenRouter-backed live `/api/v1/answer` verification is deferred to the final deployment/hardening gate rather than blocking Phase 4 closure
- Runtime note: per the same execution policy, live OpenRouter-backed eval runs and the GitHub Actions PR gate remain deferred to the final deployment/hardening gate rather than blocking Phase 5 closure
- Runtime note: LangSmith remains env-gated and was not live-verified because `LANGSMITH_API_KEY` is optional and not required for intermediate phase closure
- Runtime note: the local `docintel` database had no prior reference-window query traffic, so Phase 7 verification seeded deterministic historical query/retrieval windows in the local DB before the one-shot drift CLI was run
- Runtime note: per the same execution policy, full `docker compose ... up -d` with the dashboard service is deferred to final deployment/hardening; Phase 8 closure used compose config validation and Streamlit render smoke checks instead

## Next Step
- Execute Phase 9 from the blueprint only:
  - harden the API and dashboard Dockerfiles, production compose overlays, and workflow definitions
  - finish the public README, release checklist, and final deployment documentation
  - run the final live verification pass for deferred Docker/OpenRouter/GitHub workflow gates
  - update all continuity docs to project-complete state, then commit and push
- Runtime gate for final deployment verification:
  - real OpenRouter-backed `/api/v1/answer`, eval runs, the PR workflow secret-backed execution, and optional LangSmith tracing remain deferred until the final live verification pass
