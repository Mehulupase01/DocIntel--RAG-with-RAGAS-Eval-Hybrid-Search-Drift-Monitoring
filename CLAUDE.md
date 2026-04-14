# A2 DocIntel Working Memory

## Project Identity
- Project: `A2 DocIntel - Production RAG with RAGAS Eval, Hybrid Search & Drift Monitoring`
- Product shape: FastAPI service + Streamlit ops dashboard for hybrid retrieval, citation-grounded RAG, RAGAS-gated CI, and Evidently drift monitoring over the EU AI Act PDF
- Repo mode: flagship, production-grade, phase-wise delivery
- Active branch: `main`

## Current Commands
- `docker compose up -d`
- `uv run --directory apps/api alembic upgrade head`
- `uv run --directory apps/api pytest`
- `uv run --directory apps/api uvicorn docintel.main:app --reload --app-dir src`
- `uv run --directory apps/api python -m docintel.tools.ingest_eu_ai_act --path <pdf>`
- `uv run --directory apps/api python -m docintel.tools.benchmark_retrieval --top-k 10`
- `uv run --directory apps/api python -m docintel.tools.run_eval`
- `uv run --directory apps/api python -m docintel.tools.run_drift`

## Active Decisions
- Modular monolith FastAPI + Postgres + pgvector + Streamlit dashboard
- Embeddings: `BAAI/bge-small-en-v1.5` (384-dim); reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- BM25 via Postgres `tsvector` + GIN; vector via pgvector HNSW (cosine)
- Fusion: Reciprocal Rank Fusion (`k=60`)
- LLM: OpenRouter; default generation `anthropic/claude-haiku-4-5`, judge `openai/gpt-4o-mini`
- Eval: RAGAS faithfulness/context_precision/context_recall/answer_relevancy with CI gate
- Drift: Evidently weekly job via APScheduler

## Current Execution Truth
- Blueprint: complete (`BLUEPRINT.md`)
- Phase 1 foundation: complete
- Phase 2 ingestion pipeline: complete
- Phase 3 retrieval layer: complete
- Phase 4 generation and citations: complete (live OpenRouter verification deferred to final deployment gate by user instruction)
- Phase 5 evaluation harness: complete (live OpenRouter judge verification deferred to final deployment gate by user instruction)
- Phase 6 observability: complete
- Verified on 2026-04-14:
  - `uv sync`
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_health.py -v`
  - `docker compose up -d`
  - in-container `GET /api/v1/health/liveness`
  - in-container `GET /api/v1/health/readiness`
- Verified on 2026-04-14 for Phase 2:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_chunker.py tests/test_embedder.py tests/test_documents.py -v`
  - `uv run python -m docintel.tools.ingest_eu_ai_act --path <official-pdf> --source-uri <official-url>`
  - ASGI `GET /api/v1/documents`
  - ASGI `GET /api/v1/documents/{id}`
- Verified on 2026-04-14 for Phase 3:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py -v`
  - `uv run python -m docintel.tools.benchmark_retrieval --top-k 10`
  - ASGI `POST /api/v1/search`
- Verified on 2026-04-14 for Phase 4:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_citation_extractor.py tests/test_answer_endpoint.py -v`
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py -v`
- Verified on 2026-04-14 for Phase 5:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_eval_runner.py -v`
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py tests/test_eval_runner.py -v`
- Verified on 2026-04-14 for Phase 6:
  - `uv run alembic upgrade head`
  - `uv run pytest tests/test_metrics.py tests/test_tracing_middleware.py -v`
  - `uv run pytest tests/test_health.py tests/test_chunker.py tests/test_embedder.py tests/test_documents.py tests/test_bm25.py tests/test_vector.py tests/test_fusion.py tests/test_reranker.py tests/test_search_endpoint.py tests/test_citation_extractor.py tests/test_answer_endpoint.py tests/test_eval_runner.py tests/test_metrics.py tests/test_tracing_middleware.py -v`
  - ASGI `POST /api/v1/search`
  - ASGI `GET /metrics`
- Phase 3 benchmark result on seeded fixture:
  - `vector_only`: precision@10 `0.100`, recall@10 `0.500`
  - `hybrid_reranked`: precision@10 `0.150`, recall@10 `0.750`
- Phase 3 retrieval verification:
  - `/api/v1/search` returned `200` against the real EU AI Act corpus and persisted `queries` plus ranked `retrievals`
- Phase 4 generation verification:
  - `/api/v1/answer` contract, persistence, citation extraction, and upstream-error handling are covered by stubbed integration tests
  - `queries`, `retrievals`, `answers`, and `citations` persistence is verified in Postgres-backed tests
- Phase 5 evaluation verification:
  - fixture schema validation, eval persistence, endpoint pagination, and CI gate exit behavior are covered by `tests/test_eval_runner.py`
  - `fixtures/eu_ai_act_qa_v1.json` now ships `25` reviewed seed cases tagged as fixture version `v0.1`
  - `.github/workflows/ragas-eval.yml` is authored for PR gating and awaits final live secret-backed verification
- Phase 6 observability verification:
  - `/metrics` exposes the required DocIntel collector names
  - tracing middleware adds `X-Request-ID`, records request latency, and increments counters
  - after one real `/api/v1/search`, `/metrics` showed non-zero `docintel_requests_total` entries for the search path
- Official AI Act verification ingest:
  - source URL: `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`
  - SHA256: `bba630444b3278e881066774002a1d7824308934f49ccfa203e65be43692f55e`
  - document id: `106ea9d5-f534-4620-873f-68ff43cabf72`
  - page count: `144`
  - chunk count: `331`
- Docker Desktop storage now lives on `D:\DockerData\wsl` and `D:\DockerData\vm-data`
- Host-side `localhost:8000` access from Windows remained unreliable after Docker recovery even while the container served healthy responses internally
- Per user direction on 2026-04-14, Docker host-port verification is no longer a phase-by-phase gate and will be revisited during final deployment/hardening
- Per user direction on 2026-04-14, OpenRouter-backed live verification for `/api/v1/answer` and later eval flows is deferred to the final deployment/hardening gate; intermediate phase closure may proceed on passing local tests and stubbed provider integration checks
- The Phase 3 benchmark CLI seeds and then cleans up a deterministic fixture so retrieval benchmarking stays repeatable without polluting the live corpus

## Update Rule
Update this file after each verified phase closure together with:
- `docs/HANDOFF.md`
- `docs/PROGRESS.md`
- `docs/DECISIONS.md`
- `docs/architecture.md`
- `docs/verification.md`
