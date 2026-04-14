from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from docintel.config import get_settings
from docintel.database import get_session_factory
from docintel.logging_setup import get_logger

from .reporter import create_drift_report

logger = get_logger(__name__)
_scheduler: AsyncIOScheduler | None = None


async def run_scheduled_drift_report() -> None:
    settings = get_settings()
    session_factory = get_session_factory()
    async with session_factory() as session:
        report = await create_drift_report(
            session=session,
            window_days=settings.drift_window_days,
            reference_window_days=settings.drift_reference_window_days,
        )
    logger.info(
        "docintel.drift_report_created",
        report_id=str(report.id),
        status=report.status.value,
        html_path=report.html_path,
    )


def start_drift_scheduler() -> AsyncIOScheduler:
    global _scheduler

    settings = get_settings()
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")

    trigger = CronTrigger.from_crontab(settings.drift_cron, timezone="UTC")
    _scheduler.add_job(
        run_scheduled_drift_report,
        trigger=trigger,
        id="weekly-drift-report",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    if not _scheduler.running:
        _scheduler.start()

    job = _scheduler.get_job("weekly-drift-report")
    logger.info(
        "docintel.drift_scheduler_started",
        job_id="weekly-drift-report",
        next_run_time=str(job.next_run_time) if job and job.next_run_time else None,
        cron=settings.drift_cron,
    )
    return _scheduler


def stop_drift_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None
