from __future__ import annotations

from dataclasses import asdict, dataclass

from docintel.config import Settings, get_settings


@dataclass(frozen=True, slots=True)
class EvalThresholds:
    faithfulness: float
    context_precision: float
    context_recall: float
    answer_relevancy: float

    def as_json(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class EvalScores:
    faithfulness: float
    context_precision: float
    context_recall: float
    answer_relevancy: float


def get_eval_thresholds(settings: Settings | None = None) -> EvalThresholds:
    resolved = settings or get_settings()
    return EvalThresholds(
        faithfulness=resolved.eval_faithfulness_threshold,
        context_precision=resolved.eval_context_precision_threshold,
        context_recall=resolved.eval_context_recall_threshold,
        answer_relevancy=resolved.eval_answer_relevancy_threshold,
    )


def case_passes(scores: EvalScores, thresholds: EvalThresholds) -> bool:
    return (
        scores.faithfulness >= thresholds.faithfulness
        and scores.context_precision >= thresholds.context_precision
        and scores.context_recall >= thresholds.context_recall
        and scores.answer_relevancy >= thresholds.answer_relevancy
    )
