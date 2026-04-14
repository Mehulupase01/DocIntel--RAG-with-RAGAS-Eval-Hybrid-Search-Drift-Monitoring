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
- On 2026-04-14, the user further changed the execution policy: OpenRouter-backed live verification for `/api/v1/answer` and subsequent eval runs is deferred to the final deployment/hardening gate. Intermediate phase closure may proceed on passing local tests and stubbed provider integration checks, with the deferral recorded in continuity docs.
- Phase 2 surfaced a production enum mismatch: SQLAlchemy `Enum` was defaulting to member names like `INGESTING`, while the Phase 1 migration created lowercase enum values like `ingesting`. The document model now pins enum persistence to `member.value` so ORM behavior matches migrated Postgres types.
- Phase 2 real-PDF verification on the official AI Act corpus surfaced dense single-block pages and annex sections that would otherwise create oversized chunks and overlong `section_path` values. The ingestion path now extracts structural heading hints more selectively, splits long blocks before embedding, and truncates persisted `section_path` strings to the schema limit.
- Direct EUR-Lex PDF endpoints were returning an AWS WAF challenge from this environment on 2026-04-14. Verification therefore used the official Publications Office download handler URL for the English PDF: `https://op.europa.eu/o/opportal-service/download-handler?format=PDF&identifier=dc8116a1-3fe6-11ef-865a-01aa75ed71a1&language=en&productionSystem=cellar`.
- Phase 2 logging hardening switched console output to UTF-8-safe writes because a real ingest failure path raised `UnicodeEncodeError` under the default Windows `cp1252` console encoding.
- Phase 3 surfaced an integration mismatch with `sentence-transformers==3.4.1`: `CrossEncoder` did not accept the earlier `model_kwargs` / `tokenizer_kwargs` constructor path in this environment. The reranker now instantiates the blueprint model directly with `CrossEncoder(settings.reranker_model, device="cpu")`, which preserved the blueprint model contract while restoring compatibility.
- Phase 3 benchmark verification now uses a deterministic seeded retrieval fixture with controlled embeddings and reranker behavior, then deletes that fixture after the run. This keeps the required vector-vs-hybrid comparison repeatable and prevents benchmark-only data from polluting the live EU AI Act corpus.
- Phase 4 keeps the blueprint’s OpenRouter-native generation contract but uses `httpx.MockTransport`-backed integration tests for intermediate verification. This preserves the real wire format, retry path, and response parsing while avoiding a false phase block when `OPENROUTER_API_KEY` is intentionally withheld until the final live verification pass.
- Phase 5 follows the same execution policy: the harness ships a real RAGAS-compatible scorer path and a real GitHub Actions workflow, but intermediate verification uses local schema/persistence/endpoint tests and stubbed scoring instead of a live OpenRouter judge. Final secret-backed workflow execution is deferred to the deployment gate.
- `fixtures/eu_ai_act_qa_v1.json` ships as file family `v1` with payload version `v0.1`, matching the blueprint’s resolved compromise: unblock the harness with 25 curated cases now, then expand to 100 cases in a later `v1.0` fixture revision.
- Phase 6 replaced the Prometheus ASGI mount with an explicit root `GET /metrics` route because Starlette's mount behavior redirected `/metrics` to `/metrics/`, which violated the blueprint's exact verification contract.
- LangSmith setup is implemented as an env-gated bootstrap that exports the expected tracing environment variables only when `LANGSMITH_API_KEY` and `LANGSMITH_TRACING=true` are both present. This keeps the API startup path stable when LangSmith is disabled.
- Phase 7 computes drift at the query-window level using four numeric features (`query_length_tokens`, `retrieval_count`, `rank_stability`, `mean_rerank_score`) plus embedded query text. `query_drift_score` persists the Evidently dataset drift share, while `payload_json` retains per-feature drift details and the rank-stability delta used in status evaluation.
- Phase 7 adds a tiny deterministic report-only jitter to embedding columns before Evidently rendering so HTML generation remains stable on low-variance windows. This avoids TSNE/KDE singularities without materially changing persisted drift scores.
- Phase 8 keeps the dashboard read-only and lightweight: analytic panels query Postgres directly through a sync SQLAlchemy engine, while the retrieval explorer calls the existing `/api/v1/search` contract over HTTP instead of duplicating retrieval logic in the UI layer.
- Phase 8 normalizes any inherited async API DSN (`postgresql+asyncpg://...`) to `postgresql+psycopg://...` inside the dashboard helper so local reuse of repo env values remains compatible with the sync Streamlit process.
- Phase 9 keeps Ruff as a real bug-and-import-order gate but narrows the repo config to `E`, `F`, `I`, and `B`, with `E501` ignored. This preserves useful lint signal without turning the hardening phase into a broad style rewrite.
- Phase 9 runs mypy inside each project environment via `uv run --directory ... --with mypy==1.18.2 ...` instead of isolated `uvx mypy`, because isolated runs do not have project dependencies installed and produced false `import-not-found` failures.
- Phase 9 hardens the dashboard Dockerfile to match the API pattern: sync dependencies before the project install, then copy the app and install the project package.
- Phase 9 also switches both runtime images to `COPY --chown=app:app` so ownership is applied during the copy step instead of via a recursive `chown -R`, which is especially expensive on this Docker Desktop setup.
- On 2026-04-14, `gh secret list` for `Mehulupase01/DocIntel--RAG-with-RAGAS-Eval-Hybrid-Search-Drift-Monitoring` returned no configured repository secrets. Live `ragas-eval` verification therefore remains blocked until `OPENROUTER_API_KEY` is added.
