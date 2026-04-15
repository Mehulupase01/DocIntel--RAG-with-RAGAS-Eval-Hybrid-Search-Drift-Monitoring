# Verification

## Phase 1 Commands

```powershell
cd "apps/api"
uv sync
uv run alembic upgrade head
uv run pytest tests/test_health.py -v
cd ../..
docker compose up -d
curl http://localhost:8000/api/v1/health/liveness
curl http://localhost:8000/api/v1/health/readiness
```

## Status
- `uv sync`: Passed on Python 3.12.10 in `apps/api` on 2026-04-14
- `uv run alembic upgrade head`: Passed on 2026-04-14 against `docintel-db`
- `uv run pytest tests/test_health.py -v`: Passed on 2026-04-14 (`3 passed`)
- `docker compose up -d`: Passed on 2026-04-14 after Docker Desktop recovery and storage migration to `D:`
- In-container `GET /api/v1/health/liveness`: Passed with `{"status":"ok"}`
- In-container `GET /api/v1/health/readiness`: Passed with `{"status":"ok","db":"connected","vector_extension":true}`
- Host-side `localhost:8000` access from Windows remained unreliable despite the container serving healthy responses internally
- Per user direction on 2026-04-14, that Windows host-port issue does not block intermediate phase closure and will be revisited during final deployment/hardening

## Phase 2 Commands

```powershell
cd "apps/api"
uv run alembic upgrade head
uv run pytest tests/test_chunker.py tests/test_embedder.py tests/test_documents.py -v
uv run python -m docintel.tools.ingest_eu_ai_act --path "..\..\data\source\eu_ai_act_2024_1689_en.pdf" --source-uri "https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar"
```

## Phase 2 Status
- `uv run alembic upgrade head`: Passed on 2026-04-14 against the main `docintel` database.
- `uv run pytest tests/test_chunker.py tests/test_embedder.py tests/test_documents.py -v`: Passed on 2026-04-14 (`8 passed`).
- Official English EU AI Act PDF source used for verification:
  - URL: `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`
  - SHA256: `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e`
- `uv run python -m docintel.tools.ingest_eu_ai_act ...`: Passed on 2026-04-14 with `status=ready`, `page_count=144`, and `chunks=331`.
- Verified persisted document:
  - id: `106ea9d5-f534-4620-873f-68ff43cabf72`
  - title: `EU AI Act`
  - status: `ready`
- ASGI `GET /api/v1/documents`: Passed on 2026-04-14 and returned the ingested document in the paginated response.
- ASGI `GET /api/v1/documents/{id}`: Passed on 2026-04-14 and returned the ingested document with metadata and `chunk_count`.
- Host-side `curl http://localhost:8000/api/v1/documents` remained unreliable on this Windows machine, so route verification used the current local ASGI app instead of Docker host-port forwarding, per the user's updated execution policy.

## Phase 3 Commands

```powershell
cd "apps/api"
uv run alembic upgrade head
uv run pytest tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py -v
uv run python -m docintel.tools.benchmark_retrieval --top-k 10
curl -X POST http://localhost:8000/api/v1/search -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"query":"What is a high-risk AI system?","strategy":"hybrid_reranked","top_k":5}'
```

## Phase 3 Status
- `uv run alembic upgrade head`: Passed on 2026-04-14 against the main `docintel` database.
- `uv run pytest tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py -v`: Passed on 2026-04-14 (`7 passed`).
- `uv run python -m docintel.tools.benchmark_retrieval --top-k 10`: Passed on 2026-04-14 using the deterministic seeded fixture.
- Benchmark result on the seeded fixture:
  - `vector_only`: precision@10 `0.100`, recall@10 `0.500`
  - `bm25_only`: precision@10 `0.150`, recall@10 `0.750`
  - `hybrid`: precision@10 `0.150`, recall@10 `0.750`
  - `hybrid_reranked`: precision@10 `0.150`, recall@10 `0.750`
- ASGI `POST /api/v1/search`: Passed on 2026-04-14 and returned `200` against the real EU AI Act corpus with persisted query and retrieval trace rows.
- Host-side `curl http://localhost:8000/api/v1/search` remains subject to flaky Windows port forwarding on this machine, so the route verification was executed against the local ASGI app per the user's updated execution policy.

## Phase 4 Commands

```powershell
cd "apps/api"
uv run alembic upgrade head
uv run pytest tests/test_citation_extractor.py tests/test_answer_endpoint.py -v
curl -X POST http://localhost:8000/api/v1/answer -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"query":"Define high-risk AI system per the EU AI Act","top_k":6}'
```

## Phase 4 Status
- `uv run alembic upgrade head`: Passed on 2026-04-14 against the main `docintel` database.
- `uv run pytest tests/test_citation_extractor.py tests/test_answer_endpoint.py -v`: Passed on 2026-04-14 (`5 passed`).
- Full regression sweep through implemented Phases 1-4 passed on 2026-04-14:
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py -v`
  - result: `23 passed`
- Stubbed OpenRouter integration verifies:
  - citation markers are extracted and removed from the final answer text
  - unknown markers are dropped
  - `/api/v1/answer` returns citation metadata mapped to real chunks
  - `queries`, `retrievals`, `answers`, and `citations` rows persist correctly
  - upstream provider failures return `502 LLM_PROVIDER_ERROR`
- Per user direction on 2026-04-14, the live OpenRouter-backed `curl /api/v1/answer` verification is deferred to the final deployment/hardening gate and does not block intermediate phase closure.

## Phase 5 Commands

```powershell
cd "apps/api"
uv run alembic upgrade head
uv run pytest tests/test_eval_runner.py -v
uv run python -m docintel.tools.run_eval --suite-version v1 --strategy hybrid_reranked
uv run python -m docintel.services.evaluation.ci_gate --fail-on-breach
```

## Phase 5 Status
- `uv run alembic upgrade head`: Passed on 2026-04-14 against the main `docintel` database.
- `uv run pytest tests/test_eval_runner.py -v`: Passed on 2026-04-14 (`4 passed`).
- Full regression sweep through implemented Phases 1-5 passed on 2026-04-14:
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py tests/test_eval_runner.py -v`
  - result: `27 passed`
- Eval tests verify:
  - fixture schema validation for `fixtures/eu_ai_act_qa_v1.json`
  - persisted `eval_runs` and `eval_cases`
  - `/api/v1/eval/runs` and `/api/v1/eval/runs/{id}/cases` pagination
  - CI gate exits non-zero on threshold breach
- `.github/workflows/ragas-eval.yml` is authored and committed for PR gating.
- Per user direction on 2026-04-14, the live OpenRouter-backed `run_eval` execution and secret-backed GitHub Actions run are deferred to the final deployment/hardening gate and do not block intermediate phase closure.

## Phase 6 Commands

```powershell
cd "apps/api"
uv run pytest tests/test_metrics.py tests/test_tracing_middleware.py -v
curl http://localhost:8000/metrics | grep docintel_
```

## Phase 6 Status
- `uv run pytest tests/test_metrics.py tests/test_tracing_middleware.py -v`: Passed on 2026-04-14 (`2 passed`).
- Full regression sweep through implemented Phases 1-6 passed on 2026-04-14:
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py tests/test_eval_runner.py tests/test_metrics.py tests/test_tracing_middleware.py -v`
  - result: `29 passed`
- In-process runtime verification on 2026-04-14:
  - ASGI `POST /api/v1/search`: returned `200`
  - ASGI `GET /metrics`: returned `200`
  - `/metrics` output contained `docintel_requests_total`, `docintel_request_duration_seconds`, and `docintel_retrieval_score`
  - `/metrics` showed a non-zero counter line for `path="/api/v1/search"`
- LangSmith live verification was not performed because `LANGSMITH_API_KEY` is optional and not required for intermediate phase closure.

## Phase 7 Commands

```powershell
docker compose up -d
cd "apps/api"
uv run alembic upgrade head
uv run pytest tests/test_drift_runner.py -v
uv run python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7
curl -H "X-API-Key: $API_KEY" http://localhost:8000/api/v1/drift/reports
```

## Phase 7 Status
- `uv run alembic upgrade head`: Passed on 2026-04-14 against the main `docintel` database.
- `uv run pytest tests/test_drift_runner.py -v`: Passed on 2026-04-14 (`4 passed`).
- Full regression sweep through implemented Phases 1-7 passed on 2026-04-14:
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py tests/test_eval_runner.py tests/test_metrics.py tests/test_tracing_middleware.py tests/test_drift_runner.py -v`
  - result: `33 passed`
- Local DB precondition note:
  - the main `docintel` database had current-window traffic but no prior 7-day reference traffic on 2026-04-14
  - deterministic historical query/retrieval windows were seeded into the local DB before the one-shot drift CLI was executed
- `uv run python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7`: Passed on 2026-04-14 and created:
  - report id: `53df52b6-07e9-49b8-8b6a-a213c35e9a37`
  - status: `alert`
  - `embedding_drift_score`: `0.10519221945645096`
  - `query_drift_score`: `1.0`
  - `retrieval_quality_delta`: `-0.729727867565463`
  - HTML artifact: `apps/api/artifacts/drift/53df52b6-07e9-49b8-8b6a-a213c35e9a37.html`
- In-process route verification on 2026-04-14:
  - ASGI `GET /api/v1/drift/reports`: returned `200`
  - response `meta.total`: `1`
  - response contained `status="alert"` and a local `html_url`
- Scheduler verification on 2026-04-14:
  - app lifespan startup logged registered job `weekly-drift-report`
  - next scheduled run reported as `2026-04-21 02:00:00+00:00`
- Host-side `curl http://localhost:8000/api/v1/drift/reports` remains subject to the same flaky Windows port forwarding, so the route verification used the local ASGI app per the user's updated execution policy.

## Phase 8 Commands

```powershell
docker compose -f docker-compose.yml -f ops/docker/compose.full.yml up -d
# Generate some traffic
curl -X POST http://localhost:8000/api/v1/search ...
curl -X POST http://localhost:8000/api/v1/answer ...
uv run python -m docintel.tools.run_eval
# Visit dashboard
start http://localhost:8501
```

## Phase 8 Status
- `uv sync` in `apps/dashboard`: Passed on 2026-04-14.
- `uv run pytest tests/test_db_queries.py -v`: Passed on 2026-04-14 (`3 passed`).
- `uv run python -m compileall app.py lib pages tests`: Passed on 2026-04-14.
- Streamlit smoke verification on 2026-04-14:
  - `AppTest` rendered `app.py`
  - `AppTest` rendered `pages/1_Eval_Trends.py`
  - `AppTest` rendered `pages/2_Drift_Reports.py`
  - `AppTest` rendered `pages/3_Cost_and_Latency.py`
  - `AppTest` rendered `pages/4_Retrieval_Explorer.py`
- `docker compose -f docker-compose.yml -f ops/docker/compose.full.yml config`: Passed on 2026-04-14.
- Per user direction on 2026-04-14, full `docker compose ... up -d` with the dashboard service is deferred to the final deployment/hardening gate instead of blocking intermediate phase closure.

## Phase 9 Commands

```powershell
uvx --from ruff==0.15.7 ruff check apps/api/src apps/api/tests apps/dashboard
uv run --directory apps/api --with mypy==1.18.2 mypy --config-file ../../mypy.ini src
uv run --directory apps/dashboard --with mypy==1.18.2 mypy --config-file ../../mypy.ini app.py lib pages
uv run --directory apps/api pytest tests -v
uv run --directory apps/dashboard pytest tests/test_db_queries.py -v
uv run --directory apps/dashboard python -m compileall app.py lib pages tests
uv run --directory apps/api python -m docintel.tools.benchmark_retrieval --top-k 10
uv run --directory apps/api python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
gh workflow run ci.yml --ref main
gh workflow run ragas-eval.yml --ref main
```

## Phase 9 Status
- `uvx --from ruff==0.15.7 ruff check apps/api/src apps/api/tests apps/dashboard`: Passed on 2026-04-15.
- `uv run --directory apps/api --with mypy==1.18.2 mypy --config-file ../../mypy.ini src`: Passed on 2026-04-15.
- `uv run --directory apps/dashboard --with mypy==1.18.2 mypy --config-file ../../mypy.ini app.py lib pages`: Passed on 2026-04-15.
- `uv lock --directory apps/api`: Passed on 2026-04-14 and re-resolved `torch` to the CPU wheel (`2.6.0+cpu`) while removing the Linux CUDA/triton packages from `apps/api/uv.lock`.
- `uv sync --directory apps/api`: Passed on 2026-04-14 after the lockfile hardening update.
- `uv run --directory apps/api pytest tests -v`: Passed on 2026-04-15 (`37 passed`).
- `uv run --directory apps/dashboard pytest tests/test_db_queries.py -v`: Passed on 2026-04-15 (`3 passed`).
- `uv run --directory apps/dashboard python -m compileall app.py lib pages tests`: Passed on 2026-04-15.
- `uv run --directory apps/api pytest tests/test_answer_endpoint.py tests/test_eval_runner.py -v`: Passed on 2026-04-15 (`11 passed`) after:
  - broader parsing for OpenRouter content payloads shaped as `output_text` parts or dict-style `{text: ...}` content
  - existing explicit local sentence-transformer embeddings passed into `ragas.evaluate()` so the live eval path no longer requires `OPENAI_API_KEY`
- `uv run --directory apps/api python -m docintel.tools.benchmark_retrieval --top-k 10`: Passed on 2026-04-15.
  - `vector_only`: precision@10 `0.100`, recall@10 `0.500`
  - `hybrid_reranked`: precision@10 `0.150`, recall@10 `0.750`
- `uv run --directory apps/api python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7`: Passed on 2026-04-15 and created:
  - report id: `3a1603f0-9ce6-482b-bf0d-4ee829c3c9fb`
  - status: `alert`
  - `embedding_drift_score`: `0.12628050186595108`
  - `query_drift_score`: `1.0`
  - `retrieval_quality_delta`: `-0.56716799512358`
  - HTML artifact: `apps/api/artifacts/drift/3a1603f0-9ce6-482b-bf0d-4ee829c3c9fb.html`
- `docker build -t docintel-dashboard:test apps/dashboard`: Passed on 2026-04-14 using the app-scoped build context and `.dockerignore`.
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`: Passed on 2026-04-15.
- `docker build -t docintel-api:test apps/api`: Timed out on 2026-04-14 after 60 minutes on this Windows Docker Desktop host while rebuilding the fresh hardened API image.
- `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`: Timed out on 2026-04-14 after 60 minutes on this Windows Docker Desktop host while waiting on the fresh API image rebuild.
- Local live route verification on 2026-04-15:
  - local uvicorn startup logged `docintel.langsmith enabled=True`
  - local `POST /api/v1/search`: returned `200` against the real EU AI Act corpus with `5` results and `EU AI Act` as the top document
  - local `POST /api/v1/answer` with the tracked default model `minimax/minimax-m2.5:free`: returned upstream `429` via `502 LLM_PROVIDER_ERROR`
  - local `POST /api/v1/answer` with verification model `anthropic/claude-haiku-4.5`: returned upstream `403 Key limit exceeded` via `502 LLM_PROVIDER_ERROR`
- Local live evaluation verification on 2026-04-15:
  - default pair run persisted errored run `3a5879fe-6be9-40fd-b635-c1ca670b8584` after upstream `429`
  - verification pair run persisted errored run `3970c7fd-b631-47a7-9f81-f7973f5fe31f` after upstream `403 Key limit exceeded`
  - the current local OpenRouter key therefore blocks both the tracked defaults and the verification pair from closing the live eval gate today
- `gh workflow run ci.yml --ref main`: Passed on GitHub run `24476974916`, including the new Ubuntu Docker image-build jobs for `apps/api` and `apps/dashboard`.
- `gh secret list -R Mehulupase01/DocIntel--RAG-with-RAGAS-Eval-Hybrid-Search-Drift-Monitoring`: returned no configured repository secrets on 2026-04-14.
- `gh workflow run ragas-eval.yml --ref main`: Passed on GitHub run `24476974864` by taking the intentional skip path while `OPENROUTER_API_KEY` remains absent at the repository level.
- GitHub Actions emitted non-blocking Node 20 deprecation warnings for `actions/checkout@v4`, `actions/setup-python@v5`, and `astral-sh/setup-uv@v4`.
