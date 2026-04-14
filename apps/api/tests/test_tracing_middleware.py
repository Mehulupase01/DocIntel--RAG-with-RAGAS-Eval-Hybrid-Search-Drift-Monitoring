from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_request_middleware_sets_request_id_and_records_latency(client):
    response = await client.get("/api/v1/health/liveness")

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")

    metrics_response = await client.get("/metrics")
    assert metrics_response.status_code == 200
    assert 'path="/api/v1/health/liveness"' in metrics_response.text
