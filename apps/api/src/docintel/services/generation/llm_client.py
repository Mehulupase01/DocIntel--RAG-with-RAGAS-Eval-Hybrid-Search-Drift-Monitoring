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
    "minimax/minimax-m2.5:free": {"input": 0.0, "output": 0.0},
    "nvidia/nemotron-3-super-120b-a12b:free": {"input": 0.0, "output": 0.0},
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
                provider_error = _extract_provider_error(data)
                if provider_error is not None:
                    code, message = provider_error
                    if code in RETRYABLE_STATUS_CODES and attempt < self.max_retries:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    raise LLMProviderError(f"OpenRouter provider error {code}: {message}")
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
    if isinstance(content, dict):
        if "text" in content and content.get("text") is not None:
            return str(content["text"]).strip()
        if "content" in content:
            return _extract_text_content(content["content"])
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                candidate = item.strip()
            elif isinstance(item, dict):
                item_type = item.get("type")
                if item_type in {"text", "output_text"} or "text" in item:
                    candidate = str(item.get("text", "")).strip()
                elif "content" in item:
                    candidate = _extract_text_content(item["content"])
                else:
                    candidate = ""
            else:
                candidate = ""
            if candidate:
                text_parts.append(candidate)
        if text_parts:
            return "\n".join(text_parts).strip()
    raise LLMProviderError("OpenRouter response content was not a string or text-part list")


def _extract_provider_error(data: dict[str, Any]) -> tuple[int | None, str] | None:
    error = data.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    message = str(error.get("message") or "Provider returned an unknown error")
    try:
        parsed_code = int(code) if code is not None else None
    except (TypeError, ValueError):
        parsed_code = None
    return parsed_code, message


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
