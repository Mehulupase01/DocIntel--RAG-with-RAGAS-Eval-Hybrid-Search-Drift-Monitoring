# Handoff

## Current Status
- Active phase: Phase 9 - Hardening
- Local hardening implementation now includes:
  - committed OpenRouter model configuration (free tier only):
    - generation: `minimax/minimax-m2.5:free`
    - judge: `nvidia/nemotron-3-super-120b-a12b:free`
  - hardened `apps/api/Dockerfile` and `apps/dashboard/Dockerfile`
  - app-scoped Docker build contexts plus per-app `.dockerignore` files
  - CPU-only `torch==2.6.0+cpu` resolution in `apps/api/uv.lock`
  - lazy RAGAS imports so the API app does not pull the full eval stack at startup
  - explicit local-embedding injection into `ragas.evaluate()` so the live eval path no longer falls back to hidden OpenAI embeddings
  - `docker-compose.prod.yml`
  - `.github/workflows/ci.yml` with Ubuntu Docker image-build jobs for both app images
  - finalized `.github/workflows/ragas-eval.yml` with model-cache caching and a conditional secret check that skips cleanly when repo secrets are absent
  - `mypy.ini`
  - expanded `README.md`, `docs/deployment.md`, and `docs/release_checklist.md`
- Local Phase 9 verification completed:
  - Ruff clean across API, tests, and dashboard
  - mypy clean for API and dashboard
  - API regression: `37 passed`
  - dashboard DB helper tests: `3 passed`
  - dashboard `compileall` pass
  - `docker build -t docintel-dashboard:test apps/dashboard` pass
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` pass
  - refreshed retrieval benchmark pass on 2026-04-15:
    - `vector_only`: precision@10 `0.100`, recall@10 `0.500`
    - `hybrid_reranked`: precision@10 `0.150`, recall@10 `0.750`
  - refreshed drift report pass on 2026-04-15:
    - report id `3a1603f0-9ce6-482b-bf0d-4ee829c3c9fb`
    - status `alert`
    - html artifact `apps/api/artifacts/drift/3a1603f0-9ce6-482b-bf0d-4ee829c3c9fb.html`
  - local uvicorn startup on 2026-04-15 logged `docintel.langsmith enabled=True`
  - local `POST /api/v1/search`: `200` on 2026-04-15 against the real EU AI Act corpus
  - local `POST /api/v1/answer` with default generation model `minimax/minimax-m2.5:free`: upstream `429 Provider returned error` on 2026-04-15 (local OpenRouter key budget exhausted)
  - local eval run with default pair persisted errored run `3a5879fe-6be9-40fd-b635-c1ca670b8584` after upstream `429`
  - `gh workflow run ci.yml --ref main`: passed on GitHub run `24476974916`, including the Ubuntu API and dashboard Docker image builds
  - `gh workflow run ragas-eval.yml --ref main`: passed in intentional skip mode on GitHub run `24476974864` because repo secrets remain absent by policy
- Phase 9 completion blockers:
  - the current local OpenRouter key is over its daily budget; final live `/api/v1/answer` and eval verification require a fresh or restored key
  - a fresh API image rebuild (`docker build apps/api` or `docker compose ... up -d --build`) still times out after 60 minutes on this Windows Docker Desktop machine, but this is local environment debt and does NOT block production deployment (GitHub Actions Linux CI is the Docker gate)
  - GitHub Actions emits non-blocking Node 20 deprecation warnings for `actions/checkout@v4`, `actions/setup-python@v5`, and `astral-sh/setup-uv@v4` (should be bumped to Node 24 in a later maintenance pass)

## Next Step
- Restore or regenerate the local OpenRouter key and re-run live `/api/v1/answer` and eval verification to close Phase 9. All other checks pass; this is the final gate before production deployment.
