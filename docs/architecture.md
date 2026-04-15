# Architecture

## Pattern
- Modular monolith: one FastAPI service for request handling and one Streamlit process for ops visibility.
- Shared Postgres 16 + pgvector data plane for documents, chunks, retrieval traces, eval runs, and drift reports.

## System Diagram

```text
┌────────────────────────────────────────────────────────────────┐
│                         Clients                                 │
│   curl / Postman      Streamlit Dashboard      GitHub Actions   │
└──────────────┬──────────────────┬──────────────────┬────────────┘
               │ HTTPS            │ HTTPS            │ HTTPS
               ▼                  ▼                  ▼
┌────────────────────────────────────────────────────────────────┐
│                  FastAPI Service (apps/api)                    │
│   /documents   /search   /answer   /eval   /drift   /health    │
└──┬──────────┬──────────┬──────────┬──────────┬──────────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌──────┐  ┌─────────┐  ┌──────────┐ ┌────────┐ ┌─────────┐
│Ingest│  │Retrieval│  │Generation│ │Eval    │ │Drift    │
│PDF→  │  │BM25 +   │  │LLM call  │ │RAGAS   │ │Evidently│
│chunks│  │pgvector │  │+citation │ │harness │ │weekly   │
│+embed│  │+ RRF +  │  │extractor │ │+CI gate│ │report   │
│      │  │reranker │  │          │ │        │ │         │
└──┬───┘  └────┬────┘  └────┬─────┘ └───┬────┘ └────┬────┘
   └───────────┴────────────┬───────────┴────────────┘
                            ▼
        ┌────────────────────────────────────────────┐
        │           PostgreSQL 16 + pgvector         │
        │ documents, chunks, queries, retrievals,    │
        │ answers, citations, eval_runs, drift       │
        └────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Technology |
|---|---|---|
| API Layer | HTTP routing, auth, request validation, OpenAPI | FastAPI 0.135.2 |
| Ingestion Module | PDF parsing, chunking, embedding, indexing | pypdf 5.4.0, sentence-transformers 3.4.1 |
| Retrieval Module | BM25, ANN, RRF fusion, reranking | pgvector 0.4.1, sentence-transformers 3.4.1 |
| Generation Module | Prompt assembly, LLM calls, citation extraction | httpx 0.28.1, OpenRouter |
| Evaluation Module | RAGAS runner, fixture execution, CI gate | ragas 0.3.5, langchain-openai 0.3.13 |
| Observability Module | LangSmith tracing, Prometheus metrics, structlog | langsmith 0.3.45, prometheus-client 0.23.1, structlog 25.4.0 |
| Drift Module | Evidently reporting, weekly scheduler, persistence | evidently 0.6.7, APScheduler 3.11.0 |
| ORM / DB | Async persistence and migrations | SQLAlchemy 2.0.48, Alembic 1.18.4 |
| Dashboard | Read-only ops UI | Streamlit 1.45.0 |

## Current Corpus State
- Verified on 2026-04-14: the official English EU AI Act PDF is ingested into the local `docintel` database.
- Source URL: `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`
- Stored document id: `106ea9d5-f534-4620-873f-68ff43cabf72`
- Corpus stats from the verified ingest: `144` pages, `331` chunks

## Current Retrieval State
- Verified on 2026-04-14: `/api/v1/search` is wired end to end on top of the ingested EU AI Act corpus.
- Retrieval strategies now implemented: `vector_only`, `bm25_only`, `hybrid`, `hybrid_reranked`.
- Persistence now includes:
  - `queries` for request metadata and retrieval settings
  - `retrievals` for ranked chunk traces and score components
  - `answers` and `citations` tables pre-created in migration `003` for Phase 4 population
- Benchmarking uses a seeded synthetic fixture for deterministic strategy comparison and cleans that fixture up after each run so the live corpus remains unchanged.

## Current Generation State
- Verified on 2026-04-14: `/api/v1/answer` is implemented with retrieval-backed prompting, OpenRouter-native generation, citation extraction, and persistence into `answers` plus `citations`.
- Persisted answer records now include:
  - model id
  - prompt and response text
  - prompt/completion token counts
  - estimated cost in USD
  - end-to-end latency and finish reason
- Intermediate verification currently relies on stubbed provider integration tests; real OpenRouter-backed calls are deferred to the final deployment/hardening gate by user instruction.

## Current Evaluation State
- Verified on 2026-04-14: the evaluation domain is implemented with persisted `eval_runs` and `eval_cases`, fixture loading, threshold evaluation, background-ready endpoints, CLI entrypoints, and a PR workflow definition.
- Current fixture assets:
  - `fixtures/eu_ai_act_qa_v1.json`
  - `fixtures/eu_ai_act_qa_v1.schema.json`
  - `fixtures/README.md`
  - `fixtures/ISSUES.md`
- Current fixture payload version: `v0.1`
- Current fixture size: `25` cases
- Intermediate verification currently relies on stubbed scoring and local persistence/endpoint tests; live OpenRouter-backed eval execution is deferred to the final deployment/hardening gate by user instruction.

## Current Observability State
- Verified on 2026-04-14: observability is wired with:
  - request tracing middleware
  - Prometheus collectors at root `GET /metrics`
  - optional LangSmith environment bootstrap
- Metrics currently instrument:
  - request counts
  - request duration
  - retrieval score components
  - LLM token totals
  - LLM cost totals
  - latest eval aggregate scores
- LangSmith remains optional and no-op when its env vars are absent.

## Current Drift State
- Verified on 2026-04-14: the drift domain is implemented with:
  - persisted `drift_reports`
  - an Evidently report over query embeddings plus query/retrieval feature drift
  - HTML artifact persistence under `apps/api/artifacts/drift/`
  - read-only `/api/v1/drift/reports` endpoints and a one-shot CLI entrypoint
  - an APScheduler weekly cron job registered at app startup
- Current drift status evaluation uses:
  - `embedding_drift_score`
  - `query_drift_score` as Evidently feature-drift share
  - `retrieval_quality_delta`
  - rank-stability delta retained in `payload_json`

## Current Dashboard State
- Verified on 2026-04-14: the dashboard domain is implemented with:
  - a Streamlit home page for KPIs
  - four pages for eval trends, drift reports, cost/latency, and retrieval exploration
  - direct read-only DB queries for analytics and a live HTTP `/search` client for exploration
  - a compose overlay exposing the dashboard on port `8501`
- Dashboard verification currently uses:
  - DB-helper tests in `apps/dashboard/tests/test_db_queries.py`
  - Streamlit `AppTest` smoke rendering for every page script
  - `docker compose ... config` validation for the full-stack overlay

## Current Hardening State
- Verified on 2026-04-14: Phase 9 hardening adds:
  - production-shaped API and dashboard Dockerfiles
  - app-scoped Docker build contexts and per-app `.dockerignore` files
  - a CPU-only `torch` resolution path for the API runtime
  - `docker-compose.prod.yml`
  - `.github/workflows/ci.yml`
  - a finalized `ragas-eval.yml` with model-cache support and a conditional secret check that skips cleanly when GitHub lacks `OPENROUTER_API_KEY`
  - a root `mypy.ini`
  - expanded public README and deployment/release documentation
- Local hardening verification currently includes:
  - Ruff clean
  - mypy clean
  - full API test suite pass
  - dashboard test and compile pass
  - dashboard image build pass
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` pass
  - refreshed retrieval benchmark pass on 2026-04-15 with `hybrid_reranked` still outperforming `vector_only`
  - refreshed drift run on 2026-04-15 producing report `3a1603f0-9ce6-482b-bf0d-4ee829c3c9fb`
  - local uvicorn verification on 2026-04-15 confirming `docintel.langsmith enabled=True`, `POST /api/v1/search` `200`, and the real live provider path for `/api/v1/answer`
- Remaining final-live blockers:
  - the current local OpenRouter key is over its daily budget, so local live answer/eval verification cannot yet pass even with the approved verification pair
  - GitHub repo secrets remain absent, so `ragas-eval.yml` stays in optional-skip mode rather than running live eval in Actions
  - local Docker Desktop still times out on a fresh hardened API image rebuild under the prod overlay even after the CPU-only torch pin and build-context optimizations, but Ubuntu CI image builds are now the authoritative container proof
