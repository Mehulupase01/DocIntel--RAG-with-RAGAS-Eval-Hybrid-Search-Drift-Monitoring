from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: dict = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    error: ErrorBody


class PageMeta(BaseModel):
    page: int
    per_page: int
    total: int


class Paginated(BaseModel, Generic[T]):
    data: list[T]
    meta: PageMeta

