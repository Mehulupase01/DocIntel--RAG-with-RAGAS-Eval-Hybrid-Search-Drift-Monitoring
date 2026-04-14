from __future__ import annotations

import argparse
import asyncio

from docintel.config import get_settings
from docintel.database import get_session_factory
from docintel.services.drift.reporter import create_drift_report


async def _main() -> None:
    parser = argparse.ArgumentParser(description="Run the DocIntel weekly drift report once.")
    parser.add_argument("--window-days", type=int, default=None)
    parser.add_argument("--reference-window-days", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await create_drift_report(
            session=session,
            window_days=args.window_days or settings.drift_window_days,
            reference_window_days=args.reference_window_days or settings.drift_reference_window_days,
        )

    print("Drift report complete")
    print(f"report_id: {report.id}")
    print(f"status: {report.status.value}")
    print(f"embedding_drift_score: {report.embedding_drift_score}")
    print(f"query_drift_score: {report.query_drift_score}")
    print(f"retrieval_quality_delta: {report.retrieval_quality_delta}")
    print(f"html_path: {report.html_path}")


if __name__ == "__main__":
    asyncio.run(_main())
