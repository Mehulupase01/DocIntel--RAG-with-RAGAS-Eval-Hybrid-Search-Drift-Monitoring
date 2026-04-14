# Deployment

## Local Full Stack

Use the dashboard overlay after the API and database are in place:

```powershell
docker compose -f docker-compose.yml -f ops/docker/compose.full.yml up -d
```

## URLs

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`

## Dashboard Environment

- `DATABASE_URL`: sync dashboard DSN, expected as `postgresql+psycopg://...`
- `API_BASE_URL`: typically `http://api:8000/api/v1` in Compose
- `API_KEY`: dashboard key for live `/search` exploration

Phase 9 will expand this document with production overlays, restart policies, and scaling notes.
