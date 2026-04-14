from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EvalRunCreate(BaseModel):
    suite_version: str = "v1"
    retrieval_strategy: Literal["vector_only", "bm25_only", "hybrid", "hybrid_reranked"] = "hybrid_reranked"
    generation_model: str | None = None
    judge_model: str | None = None
    fail_fast: bool = False


class EvalRunOut(BaseModel):
    id: uuid.UUID
    suite_version: str
    git_sha: str | None
    generation_model: str
    judge_model: str
    retrieval_strategy: str
    status: str
    total_cases: int
    cases_passed: int
    faithfulness_mean: float | None
    context_precision_mean: float | None
    context_recall_mean: float | None
    answer_relevancy_mean: float | None
    thresholds_json: dict
    started_at: datetime
    finished_at: datetime | None


class EvalCaseOut(BaseModel):
    id: uuid.UUID
    fixture_case_id: str
    question: str
    ground_truth: str
    generated_answer: str
    contexts_json: list[str]
    faithfulness: float | None
    context_precision: float | None
    context_recall: float | None
    answer_relevancy: float | None
    passed: bool
    created_at: datetime
