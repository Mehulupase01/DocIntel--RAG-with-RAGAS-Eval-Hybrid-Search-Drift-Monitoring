# Handoff

## Current Status
- Active phase: Phase 9 - Hardening
- Local hardening implementation now includes:
  - hardened `apps/api/Dockerfile` and `apps/dashboard/Dockerfile`
  - app-scoped Docker build contexts plus per-app `.dockerignore` files
  - CPU-only `torch==2.6.0+cpu` resolution in `apps/api/uv.lock`
  - lazy RAGAS imports so the API app does not pull the full eval stack at startup
  - `docker-compose.prod.yml`
  - `.github/workflows/ci.yml`
  - finalized `.github/workflows/ragas-eval.yml` with model-cache caching and an explicit secret preflight
  - `mypy.ini`
  - expanded `README.md`, `docs/deployment.md`, and `docs/release_checklist.md`
- Local Phase 9 verification completed:
  - Ruff clean across API, tests, and dashboard
  - mypy clean for API and dashboard
  - API regression: `33 passed`
  - dashboard DB helper tests: `3 passed`
  - dashboard `compileall` pass
  - `docker build -t docintel-dashboard:test apps/dashboard` pass
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` pass
  - `gh workflow run ci.yml --ref main` passed on GitHub run `24394769593`
- Current blockers:
  - `gh secret list` shows no configured repo secrets, so `OPENROUTER_API_KEY` is still absent for the live `ragas-eval` workflow gate
  - `gh workflow run ragas-eval.yml --ref main` failed as expected on the explicit secret preflight in GitHub run `24393783852`
  - a fresh API image rebuild (`docker build apps/api` or `docker compose ... up -d --build`) still timed out after 60 minutes on this Windows Docker Desktop machine even after the CPU-only torch pin, lazy eval imports, and app-scoped Docker contexts

## Next Step
- Push the current Phase 9 hardening work to `main`.
- Run `gh workflow run ci.yml --ref main` and confirm it goes green on GitHub.
- Add repo secret `OPENROUTER_API_KEY`, then re-run `gh workflow run ragas-eval.yml --ref main`.
- Re-verify the prod overlay on a stable Docker host or after resolving the local Docker Desktop API image rebuild/export bottleneck.
