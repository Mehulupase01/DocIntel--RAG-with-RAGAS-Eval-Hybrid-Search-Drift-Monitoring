# Decision Log

## Blueprint Decisions

| ID | Decision | Alternatives Considered | Rationale |
|---|---|---|---|
| D-001 | Modular monolith (single FastAPI service) | Microservices per domain | One request lifecycle spans all domains; no independent scaling need at this corpus size |
| D-002 | Postgres + pgvector for both BM25 (tsvector) and ANN | Qdrant/Weaviate; rank-bm25 in-memory | One service to operate; both indexes in the same transaction |
| D-003 | Reciprocal Rank Fusion (k=60) for score fusion | Weighted normalized scores; Borda count | RRF needs no per-source score normalization; k=60 is the literature default |
| D-004 | bge-small-en-v1.5 (384-dim) for embeddings | all-MiniLM-L6-v2 (faster but lower quality); bge-large (heavier) | Best small-model RAG quality at 384-dim; CPU-friendly |
| D-005 | cross-encoder/ms-marco-MiniLM-L-6-v2 for reranking | ColBERT, mxbai-rerank | Smallest production-credible reranker; matches brief; CPU-acceptable |
| D-006 | OpenRouter as the LLM gateway | Direct OpenAI; direct Anthropic | Single key, model-agnostic, lets us swap models in eval runs; matches user pattern |
| D-007 | RAGAS with `langchain-openai` judge against OpenRouter | DeepEval; Phoenix | Brief specifies RAGAS; LangSmith ecosystem alignment |
| D-008 | API key auth (X-API-Key) for v1 | JWT; OAuth | Internal/ops use; simple to rotate; JWT is cheap to migrate to later |
| D-009 | Streamlit dashboard | Next.js | Read-only ops UI; ships in hours; brief specifies Streamlit |
| D-010 | APScheduler in-process weekly drift job | Celery + Redis; Cron + container | Single-instance deployment; no extra service |
| D-011 | HNSW index (m=16, ef_construction=64) | IVFFlat | HNSW is the modern pgvector default with better recall/latency tradeoff at this scale |
| D-012 | Generated columns for `tsvector` (`Computed`) | Trigger-maintained tsvector | Postgres 12+ generated columns are simpler and fully indexable |
| D-013 | uv as package manager | poetry; pip-tools | Matches sibling projects; faster resolves |
| D-014 | structlog for logging | std logging only | JSON logs out of the box; trivial integration with request middleware |
| D-015 | Ship v0.1 fixture with 25 cases (LLM-seeded + reviewed), grow to 100 v1.0 | Block on hand-curating 100 cases up front | Unblocks Phase 5 verification while preserving the success-criteria target as a follow-up |
| D-016 | All LLM calls (generation + RAGAS judge) route through OpenRouter; request/config fields accept any OpenRouter-hosted model ID | Hardcode per-provider SDKs (Anthropic + OpenAI directly) | Single API surface and credential; RAGAS uses `langchain-openai` with `base_url=OPENROUTER_BASE_URL`; switching models is a one-string change at request or env level |
| D-017 | Default generation model: `anthropic/claude-haiku-4-5` | `claude-sonnet-4-6`, `gpt-4o-mini`, `gpt-4o` | Best speed/quality/cost for citation-grounded regulatory answers; confirmed by user 2026-04-13 |
| D-018 | Default judge model: `openai/gpt-4o-mini` (via OpenRouter) | `gpt-4o`, `claude-haiku-4-5`, `claude-sonnet-4-6` | RAGAS prompts are OpenAI-tuned; mini keeps CI cost bounded; confirmed by user 2026-04-13 |
| D-019 | API key (`X-API-Key`) is the committed v1 auth scheme | JWT Bearer, no-auth | Ops/dashboard/CI use; JWT is a cheap future migration when a public web UI is added; confirmed by user 2026-04-13 |

## Execution Notes
- Phase 1 dependency pin validation completed locally on 2026-04-13 and surfaced a resolver conflict between `pytest==9.0.2` and `pytest-asyncio==1.0.0` because `pytest-asyncio` pins `pytest<9`.
- Phase 1 implementation therefore uses `pytest==8.4.2` as the smallest compatible adjustment needed to keep `pytest-asyncio==1.0.0` and unblock the blueprint verification workflow.
- Phase 1 dependency validation also surfaced that `langchain==0.3.27` now requires `langsmith>=0.3.45`, so `langsmith` was raised from the blueprint pin `0.3.20` to the minimum compatible version `0.3.45`.
- Phase 1 config hardening added tolerant parsing for ambient `DEBUG` values such as `release` and `production`, because a machine-level `DEBUG=release` was overriding the repo `.env` and breaking local command execution.
- Docker Desktop storage was migrated on 2026-04-13/14 to `D:\DockerData\wsl` and `D:\DockerData\vm-data` to recover `C:` space and stabilize WSL-backed containers.
- On 2026-04-14, the user explicitly changed the execution policy: Docker host-port verification is no longer required at the end of every phase and will instead be revisited during final deployment/hardening if local Windows port forwarding remains flaky.
