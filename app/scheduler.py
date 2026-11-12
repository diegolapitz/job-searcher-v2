from __future__ import annotations

import logging
import time

from app.config import settings
from app.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def run_scheduler(
    *,
    interval_hours: float | None = None,
    notify: bool = True,
    only_sources: set[str] | None = None,
    max_requests: int | None = None,
    run_now: bool = True,
    max_cycles: int | None = None,
) -> None:
    configured_interval = (
        interval_hours if interval_hours is not None else settings()["interval_hours"]
    )
    interval = float(configured_interval)
    if interval <= 0:
        raise ValueError("Scheduler interval must be greater than zero")
    if max_cycles is not None and max_cycles <= 0:
        raise ValueError("Scheduler max_cycles must be greater than zero")

    logger.info("Scheduler started with interval %.2f hours", interval)
    first_iteration = True
    cycles = 0
    while max_cycles is None or cycles < max_cycles:
        if run_now or not first_iteration:
            try:
                result = run_pipeline(
                    notify=notify,
                    only_sources=only_sources,
                    max_requests=max_requests,
                )
                logger.info("Scheduled run completed: %s", result)
            except Exception:
                logger.exception("Scheduled run failed; scheduler will continue")
        first_iteration = False
        cycles += 1
        if max_cycles is not None and cycles >= max_cycles:
            return
        next_run_seconds = interval * 3600
        logger.info("Next scheduled run in %.2f hours", interval)
        time.sleep(next_run_seconds)
