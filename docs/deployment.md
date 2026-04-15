# Deployment

## Compose Layers

### Base local stack

```powershell
docker compose up -d
```

This starts:

- `db`: PostgreSQL 16 + pgvector
- `api`: FastAPI service on `http://localhost:8000`

### Full local stack with dashboard

```powershell
docker compose -f docker-compose.yml -f ops/docker/compose.full.yml up -d
```

This adds:

- `dashboard`: Streamlit UI on `http://localhost:8501`

### Production-shaped overlay

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
```

The production overlay adds:

- pinned image tags for `docintel-api:0.1.0` and `docintel-dashboard:0.1.0`
- restart policies
- resource limits
- a named `artifacts_data` volume for persisted outputs
- the dashboard service definition needed for a single-command stack bring-up

## Runtime URLs

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`
- Metrics: `http://localhost:8000/metrics`

## Required Environment

### Core runtime

- `DATABASE_URL`
- `API_KEYS`
- `SECRET_KEY`
- `MODEL_CACHE_DIR`
- `ARTIFACT_STORAGE_PATH`

### Live generation and evaluation

- `OPENROUTER_API_KEY`

### Optional tracing

- `LANGSMITH_API_KEY`
- `LANGSMITH_PROJECT`
- `LANGSMITH_TRACING`

## Dashboard Environment

- `DATABASE_URL`: sync DSN, expected as `postgresql+psycopg://...`
- `API_BASE_URL`: usually `http://api:8000/api/v1` inside Compose
- `API_KEY`: dashboard key for the live retrieval explorer

## Model Cache and Artifacts

- API containers expect `/app/.model_cache`
- API containers write artifacts to `/app/artifacts`
- dashboard containers do not need the embedding cache
- GitHub Actions caches `apps/api/.model_cache` for the `ragas-eval` workflow
- The API lockfile now pins `torch` to the explicit CPU wheel source, matching the blueprint's CPU-only inference assumption and avoiding bundled CUDA libraries in fresh installs

## GitHub Actions Secrets

As of 2026-04-15, the authenticated CLI still sees no configured repo secrets for:

```text
Mehulupase01/DocIntel--RAG-with-RAGAS-Eval-Hybrid-Search-Drift-Monitoring
```

Under the current local-only secret policy, this is acceptable. The repo now treats GitHub-hosted live eval as optional automation, not as a required release gate.

If you do want GitHub-hosted live eval later, configure:

- `OPENROUTER_API_KEY`
- optionally `LANGSMITH_API_KEY`

## Scaling Notes

- The current APScheduler drift job assumes a single API instance.
- If the API is horizontally scaled later, drift scheduling should move to a dedicated worker or external scheduler.
- Retrieval and ingestion are CPU-bound on this stack; keep `model_cache` persistent across restarts to avoid repeated cold downloads.
- The API image is materially heavier than the dashboard image because it includes the embedding and reranker runtime.

## Current Machine Caveats

- `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` is verified locally.
- `docker build -t docintel-dashboard:test apps/dashboard` is verified locally from the app-scoped build context.
- On this Windows Docker Desktop host, a fresh API image rebuild (`docker build apps/api` or `docker compose ... up -d --build`) still times out after 60 minutes even after the CPU-only torch pin, lazy RAGAS imports, and smaller build contexts.
- The authoritative container proof now lives in Ubuntu GitHub Actions image builds for `apps/api` and `apps/dashboard`, not in this Windows host's fresh API rebuild path.
- The Dockerfiles are production-shaped and locally validated as far as Ruff, mypy, pytest, dashboard image build, and Compose config are concerned, but a clean full-stack prod-overlay bring-up is still best re-verified on a stable Linux Docker host if this Windows Docker Desktop bottleneck persists.

## Local Live Verification Policy

- Tracked runtime defaults remain:
  - generation: `minimax/minimax-m2.5:free`
  - judge: `nvidia/nemotron-3-super-120b-a12b:free`
- Approved verification-only backup pair:
  - generation: `anthropic/claude-haiku-4.5`
  - judge: `openai/gpt-4o-mini`
- Release verification should try the tracked defaults first.
- If the default generation model fails with a provider-classified limit error, re-run the same local live answer check with `anthropic/claude-haiku-4.5`.
- If the default eval lane fails with a provider-classified limit or timeout error, re-run the local eval lane with `anthropic/claude-haiku-4.5` plus `openai/gpt-4o-mini`.

## Recommended Final Release Pass

1. Push the latest Phase 9 hardening commit.
2. Run `gh workflow run ci.yml --ref main` and confirm the Ubuntu lint, typecheck, test, and Docker image-build jobs are green.
3. Run the local live answer verification with the local-only `OPENROUTER_API_KEY`.
4. Run the local live eval verification with the local-only `OPENROUTER_API_KEY`.
5. Review the latest retrieval benchmark and drift report outputs.
6. Optionally configure `OPENROUTER_API_KEY` as a GitHub repository secret and run `gh workflow run ragas-eval.yml --ref main` if GitHub-hosted live eval is desired.
