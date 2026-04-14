from __future__ import annotations

from docintel.database import get_db
from docintel.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/liveness")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/readiness")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "db": "connected",
        "vector_extension": True,
    }


class BrokenSession:
    async def execute(self, *_args, **_kwargs):
        raise SQLAlchemyError("database unavailable")


async def test_readiness_db_down() -> None:
    app.dependency_overrides[get_db] = lambda: BrokenSession()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/health/readiness")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "db": "disconnected",
        "vector_extension": False,
    }

