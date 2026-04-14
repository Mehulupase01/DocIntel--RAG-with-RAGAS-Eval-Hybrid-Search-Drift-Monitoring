# Handoff

## Current Status
- Active phase: Phase 9 - Hardening
- Local hardening implementation now includes:
  - hardened `apps/api/Dockerfile` and `apps/dashboard/Dockerfile`
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
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` pass
  - `gh workflow run ci.yml --ref main` passed on GitHub run `24394769593`
- Current blockers:
  - `gh secret list` shows no configured repo secrets, so `OPENROUTER_API_KEY` is still absent for the live `ragas-eval` workflow gate
  - `gh workflow run ragas-eval.yml --ref main` failed as expected on the explicit secret preflight in GitHub run `24393783852`
  - local prod-overlay `docker compose ... up -d` brings up `db` and `api`, but the dashboard image export/build path remains unreliable on this Windows Docker Desktop machine even after Dockerfile and `.dockerignore` improvements

## Next Step
- Push the current Phase 9 hardening work to `main`.
- Run `gh workflow run ci.yml --ref main` and confirm it goes green on GitHub.
- Add repo secret `OPENROUTER_API_KEY`, then re-run `gh workflow run ragas-eval.yml --ref main`.
- Re-verify the prod overlay on a stable Docker host or after resolving the local Docker Desktop dashboard export issue.
