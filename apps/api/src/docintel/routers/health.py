"""Health check routes."""

from __future__ import annotations

from typing import Annotated, cast

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from docintel.database import check_vector_extension, get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/liveness")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness")
async def readiness(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | bool]:
    try:
        await db.execute(text("SELECT 1"))
        vector_extension = await check_vector_extension(db)
    except Exception:
        return cast(
            dict[str, str | bool],
            JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "db": "disconnected", "vector_extension": False},
            ),
        )

    if not vector_extension:
        return cast(
            dict[str, str | bool],
            JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "error", "db": "connected", "vector_extension": False},
            ),
        )

    return {"status": "ok", "db": "connected", "vector_extension": True}
