# Release Checklist

## Hard Gates

- [ ] `uvx --from ruff==0.15.7 ruff check apps/api/src apps/api/tests apps/dashboard`
- [ ] `uv run --directory apps/api --with mypy==1.18.2 mypy --config-file ../../mypy.ini src`
- [ ] `uv run --directory apps/dashboard --with mypy==1.18.2 mypy --config-file ../../mypy.ini app.py lib pages`
- [ ] `uv run --directory apps/api pytest tests -v`
- [ ] `uv run --directory apps/dashboard pytest tests/test_db_queries.py -v`
- [ ] `uv run --directory apps/dashboard python -m compileall app.py lib pages tests`
- [ ] `uv run --directory apps/api python -m docintel.tools.benchmark_retrieval --top-k 10`
- [ ] `uv run --directory apps/api python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`
- [ ] `gh workflow run ci.yml --ref main`
- [ ] Ubuntu CI image builds for `apps/api` and `apps/dashboard` complete successfully in `ci.yml`
- [ ] Local live `/api/v1/answer` verification succeeds on the tracked default model or on the approved verification model after a documented provider-classified default failure
- [ ] Local live eval verification succeeds on the tracked default pair or on the approved verification pair after a documented provider-classified default failure

## Data and Quality

- [ ] Official EU AI Act corpus is present and searchable
- [ ] Retrieval benchmark still shows hybrid outperforming vector-only
- [ ] Latest eval run meets target thresholds or deviations are documented
- [ ] Latest drift report is reviewed and does not show unexplained alerting

## Runtime

- [ ] Production `API_KEYS` values are configured
- [ ] Optional `LANGSMITH_API_KEY` is configured if tracing is meant to be live

## Optional Automation

- [ ] Repository secret `OPENROUTER_API_KEY` is configured if GitHub-hosted live `ragas-eval` should run instead of skipping by policy
- [ ] `gh workflow run ragas-eval.yml --ref main` is green when the repo secret is configured
- [ ] Full prod-overlay `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` is re-verified on a stable Linux/Docker host if local Windows Docker Desktop remains unreliable

## Docs

- [ ] README matches the currently verified commands
- [ ] `docs/deployment.md` reflects the compose overlays and environment variables
- [ ] `docs/verification.md` reflects the actual latest verification state
- [ ] `CLAUDE.md`, `docs/HANDOFF.md`, and `docs/PROGRESS.md` show the project-complete state
