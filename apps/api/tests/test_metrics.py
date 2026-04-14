from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_metrics_exposes_collectors(client):
    response = await client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "docintel_requests_total" in body
    assert "docintel_request_duration_seconds" in body
    assert "docintel_retrieval_score" in body
    assert "docintel_llm_tokens_total" in body
    assert "docintel_llm_cost_usd_total" in body
    assert "docintel_eval_score" in body
