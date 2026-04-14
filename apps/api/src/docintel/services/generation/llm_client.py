from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from time import perf_counter
from typing import Any

import httpx

from docintel.config import get_settings

KNOWN_MODEL_PRICING_USD_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "anthropic/claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "anthropic/claude-haiku-4.5": {"input": 1.0, "output": 5.0},
    "openai/gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class LLMProviderError(RuntimeError):
    """Raised when the upstream LLM provider request fails."""


class LLMProviderNotConfiguredError(RuntimeError):
    """Raised when the OpenRouter credential is missing."""


@dataclass(slots=True)
class LLMGeneration:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    latency_ms: int
    finish_reason: str | None


class OpenRouterClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        max_retries: int = 3,
        timeout_seconds: float = 60.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.openrouter_api_key
        self.base_url = (base_url or settings.openrouter_base_url).rstrip("/")
        self.max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(base_url=self.base_url, timeout=timeout_seconds)

    async def generate(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMGeneration:
        if not self.api_key:
            raise LLMProviderNotConfiguredError("OPENROUTER_API_KEY is not configured")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            start = perf_counter()
            try:
                response = await self._client.post("chat/completions", headers=headers, json=payload)
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue

                response.raise_for_status()
                latency_ms = int((perf_counter() - start) * 1000)
                data = response.json()
                return self._parse_response(data, requested_model=model, latency_ms=latency_ms)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in RETRYABLE_STATUS_CODES:
                    if attempt < self.max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                if isinstance(exc, httpx.RequestError) and attempt < self.max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue
                break

        raise LLMProviderError(f"OpenRouter request failed: {last_error}") from last_error

    def _parse_response(self, data: dict[str, Any], *, requested_model: str, latency_ms: int) -> LLMGeneration:
        choices = data.get("choices") or []
        if not choices:
            raise LLMProviderError("OpenRouter response did not include any choices")

        message = choices[0].get("message") or {}
        text = _extract_text_content(message.get("content"))
        usage = data.get("usage") or {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        resolved_model = str(data.get("model") or requested_model)

        return LLMGeneration(
            text=text,
            model=resolved_model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=_estimate_cost_usd(resolved_model, prompt_tokens, completion_tokens),
            latency_ms=latency_ms,
            finish_reason=choices[0].get("finish_reason"),
        )


def _extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        text_parts = [str(item.get("text", "")) for item in content if isinstance(item, dict) and item.get("type") == "text"]
        return "\n".join(part for part in text_parts if part).strip()
    raise LLMProviderError("OpenRouter response content was not a string or text-part list")


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = KNOWN_MODEL_PRICING_USD_PER_1M_TOKENS.get(model)
    if pricing is None:
        return 0.0
    return round(
        (prompt_tokens / 1_000_000) * pricing["input"] + (completion_tokens / 1_000_000) * pricing["output"],
        6,
    )


@lru_cache
def get_openrouter_client() -> OpenRouterClient:
    return OpenRouterClient()
