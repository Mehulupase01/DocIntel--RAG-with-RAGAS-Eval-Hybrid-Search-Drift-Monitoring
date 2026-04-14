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
