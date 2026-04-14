# Progress

| Phase | Status | Notes |
|---|---|---|
| Phase 0 - Blueprint | Complete | `BLUEPRINT.md` is the authoritative architecture source. |
| Phase 1 - Foundation | Complete | FastAPI foundation, async DB layer, Alembic baseline, tests, Docker assets, Docker storage migration to `D:`, and continuity docs are in place. Core verification commands passed on 2026-04-14. |
| Phase 2 - Ingestion Pipeline | Complete | Documents/chunks models, migration 002, ingestion services, `/documents` routes, CLI ingest, tests, and a verified official EU AI Act ingest (`144` pages, `331` chunks) are complete as of 2026-04-14. |
| Phase 3 - Retrieval Layer | Complete | Queries/retrievals models, migration 003, BM25 + pgvector + RRF + reranker services, `/search`, retrieval benchmark CLI, and retrieval tests are complete as of 2026-04-14. Seeded benchmark verification showed `hybrid_reranked` outperforming `vector_only` on precision@10 (`0.150` vs `0.100`). |
| Phase 4 - Generation & Citations | Complete | Answer/citation models, `/answer`, OpenRouter client, prompt/citation services, API docs, and provider-stubbed integration tests are complete as of 2026-04-14. Live OpenRouter verification is intentionally deferred to the final deployment gate by user instruction. |
| Phase 5 - Evaluation Harness | In Progress | Runtime OpenRouter verification is deferred to the final gate; local implementation and stubbed verification proceed now. |
| Phase 6 - Observability | Not Started | LangSmith remains env-gated. |
| Phase 7 - Drift Monitoring | Not Started | Blocked until retrieval and eval flows exist. |
| Phase 8 - Streamlit Dashboard | Not Started | Blocked until API and monitoring data exist. |
| Phase 9 - Hardening | Not Started | Final release and README phase. |
