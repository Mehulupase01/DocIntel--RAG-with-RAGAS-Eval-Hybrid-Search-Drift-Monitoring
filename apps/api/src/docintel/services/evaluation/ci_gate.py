from __future__ import annotations

import argparse
import asyncio

from docintel.database import get_session_factory
from docintel.schemas.eval import EvalRunCreate
from docintel.services.evaluation.ragas_runner import run_eval_suite


async def _main() -> int:
    parser = argparse.ArgumentParser(description="Run the DocIntel RAGAS CI gate.")
    parser.add_argument("--suite-version", default="v1")
    parser.add_argument("--strategy", default="hybrid_reranked")
    parser.add_argument("--generation-model", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--fail-on-breach", action="store_true")
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
            ),
        )

    print(
        f"run_id={result.run_id} status={result.status.value} "
        f"cases_passed={result.cases_passed}/{result.total_cases}"
    )
    if args.fail_on_breach and result.status.value != "passed":
        return 1
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_main()))


if __name__ == "__main__":
    main()
