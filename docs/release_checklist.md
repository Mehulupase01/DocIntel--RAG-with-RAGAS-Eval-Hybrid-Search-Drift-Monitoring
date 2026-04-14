# Release Checklist

## Pre-Release

- [ ] `uv run --directory apps/api pytest tests -v`
- [ ] `uv run --directory apps/dashboard pytest tests/test_db_queries.py -v`
- [ ] `uvx --from ruff==0.15.7 ruff check apps/api/src apps/api/tests apps/dashboard`
- [ ] `uv run --directory apps/api --with mypy==1.18.2 mypy --config-file ../../mypy.ini src`
- [ ] `uv run --directory apps/dashboard --with mypy==1.18.2 mypy --config-file ../../mypy.ini app.py lib pages`
- [ ] `uv run --directory apps/api python -m docintel.tools.run_drift --window-days 7 --reference-window-days 7`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`
- [ ] `gh workflow run ci.yml --ref main`
- [ ] `gh workflow run ragas-eval.yml --ref main`

## Data and Quality

- [ ] Official EU AI Act corpus is present and searchable
- [ ] Retrieval benchmark still shows hybrid outperforming vector-only
- [ ] Latest eval run meets target thresholds or deviations are documented
- [ ] Latest drift report is reviewed and does not show unexplained alerting

## Secrets and Runtime

- [ ] Repository secret `OPENROUTER_API_KEY` is configured
- [ ] Production `API_KEYS` values are configured
- [ ] Optional `LANGSMITH_API_KEY` is configured if tracing is meant to be live

## Docs

- [ ] README matches the currently verified commands
- [ ] `docs/deployment.md` reflects the compose overlays and environment variables
- [ ] `docs/verification.md` reflects the actual latest verification state
- [ ] `CLAUDE.md`, `docs/HANDOFF.md`, and `docs/PROGRESS.md` show the project-complete state
