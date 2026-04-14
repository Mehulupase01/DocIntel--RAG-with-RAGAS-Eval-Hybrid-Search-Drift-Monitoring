# Verification

## Phase 1 Commands

```powershell
cd "apps/api"
uv sync
uv run alembic upgrade head
uv run pytest tests/test_health.py -v
cd ../..
docker compose up -d
curl http://localhost:8000/api/v1/health/liveness
curl http://localhost:8000/api/v1/health/readiness
```

## Status
- `uv sync`: Passed on Python 3.12.10 in `apps/api` on 2026-04-14
- `uv run alembic upgrade head`: Passed on 2026-04-14 against `docintel-db`
- `uv run pytest tests/test_health.py -v`: Passed on 2026-04-14 (`3 passed`)
- `docker compose up -d`: Passed on 2026-04-14 after Docker Desktop recovery and storage migration to `D:`
- In-container `GET /api/v1/health/liveness`: Passed with `{"status":"ok"}`
- In-container `GET /api/v1/health/readiness`: Passed with `{"status":"ok","db":"connected","vector_extension":true}`
- Host-side `localhost:8000` access from Windows remained unreliable despite the container serving healthy responses internally
- Per user direction on 2026-04-14, that Windows host-port issue does not block intermediate phase closure and will be revisited during final deployment/hardening
