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
