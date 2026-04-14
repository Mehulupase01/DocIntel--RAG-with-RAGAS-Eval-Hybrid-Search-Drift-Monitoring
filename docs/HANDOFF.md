# Handoff

## Current Status
- Active phase: Phase 5 - Evaluation Harness
- Phase 4 objective: `/api/v1/answer` returns citation-grounded answers, persists `answers` plus `citations`, and tracks tokens, cost, and latency per request
- Phase 4 delivered:
  - `Answer` and `Citation` ORM models wired into the existing `Query` and migration `003` table set
  - answer schemas and authenticated `POST /api/v1/answer`
  - generation services for prompt construction, OpenRouter calls, citation extraction, and answer orchestration
  - provider cost estimation and retry handling in the OpenRouter client
  - API docs for `/search` and `/answer`
  - citation extractor tests and Postgres-backed answer endpoint integration tests
- Phase 4 verified:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_citation_extractor.py tests/test_answer_endpoint.py -v` (`5 passed`)
  - full regression sweep through Phases 1-4: `23 passed`
  - provider-success, provider-failure, answer persistence, and citation metadata are verified through stubbed OpenRouter integration tests
- Residual environment note: Windows host access to `localhost:8000` remains flaky, so current-phase route verification used in-process ASGI calls per the user's updated execution policy
- Runtime note: per user direction on 2026-04-14, OpenRouter-backed live `/api/v1/answer` verification is deferred to the final deployment/hardening gate rather than blocking Phase 4 closure

## Next Step
- Execute Phase 5 from the blueprint only:
  - add eval run models, schemas, and migration `004_eval_runs_and_cases.py`
  - implement fixture loading, threshold logic, RAGAS runner, CI gate, `/eval/runs*` endpoints, and CLI tools
  - create the approved `v0.1` 25-case fixture plus schema and curation docs
  - verify Phase 5 locally with stubbed judge tests, then commit and push
- Runtime gate for final deployment verification:
  - real OpenRouter-backed `/api/v1/answer` and eval runs remain deferred until the final live verification pass
