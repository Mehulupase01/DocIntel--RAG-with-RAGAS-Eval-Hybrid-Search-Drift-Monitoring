from __future__ import annotations

import argparse
import asyncio

from docintel.database import get_session_factory
from docintel.schemas.eval import EvalRunCreate
from docintel.services.evaluation.ragas_runner import run_eval_suite


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the DocIntel evaluation suite.")
    parser.add_argument("--suite-version", default="v1")
    parser.add_argument("--strategy", default="hybrid_reranked")
    parser.add_argument("--generation-model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args()

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await run_eval_suite(
            session=session,
            request=EvalRunCreate(
                suite_version=args.suite_version,
                retrieval_strategy=args.strategy,
                generation_model=args.generation_model,
                judge_model=args.judge_model,
                fail_fast=args.fail_fast,
            ),
        )

    print("Eval run complete")
    print(f"run_id: {result.run_id}")
    print(f"status: {result.status.value}")
    print(f"cases_passed: {result.cases_passed}/{result.total_cases}")
    print(f"faithfulness_mean: {result.faithfulness_mean}")
    print(f"context_precision_mean: {result.context_precision_mean}")
    print(f"context_recall_mean: {result.context_recall_mean}")
    print(f"answer_relevancy_mean: {result.answer_relevancy_mean}")


if __name__ == "__main__":
    asyncio.run(_main())
