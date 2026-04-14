from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.auth import require_api_key
from docintel.database import get_db
from docintel.schemas.answer import AnswerRequest, AnswerResponse
from docintel.schemas.common import ErrorEnvelope
from docintel.services.generation.answerer import answer_question
from docintel.services.generation.llm_client import LLMProviderError, LLMProviderNotConfiguredError

router = APIRouter(prefix="/answer", tags=["answer"])


@router.post(
    "",
    response_model=AnswerResponse,
    responses={
        401: {"model": ErrorEnvelope},
        422: {"model": ErrorEnvelope},
        502: {"model": ErrorEnvelope},
        503: {"model": ErrorEnvelope},
    },
)
async def answer(
    request: AnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(require_api_key)],
) -> AnswerResponse:
    try:
        result = await answer_question(session=db, request=request)
    except LLMProviderNotConfiguredError as exc:
        return _error_response(status.HTTP_503_SERVICE_UNAVAILABLE, "LLM_PROVIDER_NOT_CONFIGURED", str(exc))
    except LLMProviderError as exc:
        return _error_response(status.HTTP_502_BAD_GATEWAY, "LLM_PROVIDER_ERROR", str(exc))

    return AnswerResponse(
        query_id=result.query_id,
        answer_id=result.answer_id,
        answer=result.answer,
        citations=result.citations,
        contexts=result.contexts,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        latency_ms=result.latency_ms,
    )


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message, "detail": {}}})
