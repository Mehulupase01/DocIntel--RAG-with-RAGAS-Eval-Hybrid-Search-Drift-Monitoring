# Handoff

## Current Status
- Active phase: Phase 9 - Hardening
- Local hardening implementation now includes:
  - default OpenRouter model override for local/runtime settings:
    - generation: `minimax/minimax-m2.5:free`
    - judge: `nvidia/nemotron-3-super-120b-a12b:free`
  - hardened `apps/api/Dockerfile` and `apps/dashboard/Dockerfile`
  - app-scoped Docker build contexts plus per-app `.dockerignore` files
  - CPU-only `torch==2.6.0+cpu` resolution in `apps/api/uv.lock`
  - lazy RAGAS imports so the API app does not pull the full eval stack at startup
  - explicit local-embedding injection into `ragas.evaluate()` so the live eval path no longer falls back to hidden OpenAI embeddings
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
  - live `/api/v1/answer` with requested default generation model `minimax/minimax-m2.5:free`: upstream provider-limit failure (`429`) on 2026-04-14
  - live `/api/v1/answer` with request override `nvidia/nemotron-3-super-120b-a12b:free`: `200` on 2026-04-14
  - live RAGAS judge smoke with `nvidia/nemotron-3-super-120b-a12b:free`: provider timeout failure (`524`) on 2026-04-14 after the local embedding fix
  - EU LangSmith project `docintel-dev`: recent runs observed from the live judge smoke, confirming tracing reaches LangSmith when enabled
  - `gh workflow run ci.yml --ref main` passed on GitHub run `24394769593`
- Current blockers:
  - `gh secret list` shows no configured repo secrets, so `OPENROUTER_API_KEY` is still absent for the GitHub-hosted `ragas-eval` workflow gate unless the user explicitly approves uploading it as a repo secret
  - `gh workflow run ragas-eval.yml --ref main` failed as expected on the explicit secret preflight in GitHub run `24393783852`
  - a fresh API image rebuild (`docker build apps/api` or `docker compose ... up -d --build`) still timed out after 60 minutes on this Windows Docker Desktop machine even after the CPU-only torch pin, lazy eval imports, and app-scoped Docker contexts
  - the user-selected free OpenRouter defaults are not yet both live-verifiable on 2026-04-14:
    - `minimax/minimax-m2.5:free` generation is returning provider-limit `429`
    - `nvidia/nemotron-3-super-120b-a12b:free` judge prompts are returning provider timeout `524`

## Next Step
- Run `gh workflow run ci.yml --ref main` and confirm it goes green on GitHub.
- If the user approves uploading the secret, add repo secret `OPENROUTER_API_KEY`, then re-run `gh workflow run ragas-eval.yml --ref main`.
- Re-attempt live generation with `minimax/minimax-m2.5:free` after the provider-limit window clears, or confirm whether the user wants a different generation default.
- Re-attempt live RAGAS judge verification with `nvidia/nemotron-3-super-120b-a12b:free`, or confirm whether the user wants a different judge model if provider `524` persists.
- Re-verify the prod overlay on a stable Docker host or after resolving the local Docker Desktop API image rebuild/export bottleneck.
