"""
Discovery scheduler — periodic auto-crawl of active keywords.

Runs as a background asyncio task started during FastAPI lifespan.
Every `discovery_crawl_interval_hours` hours (default: 24h) it calls
bulk_launch_from_keywords() to create and dispatch jobs for all
active keywords that haven't been crawled recently.

Design:
  - Single asyncio.Task per process (no external scheduler/cron needed).
  - Graceful shutdown: task is cancelled on app shutdown, current sleep
    is interrupted cleanly — no data loss because jobs are DB-persisted.
  - Idempotent: bulk_launch checks last_crawled_at so re-running early
    skips already-crawled keywords.

Startup / shutdown:
  Called from app.main lifespan context:

    @asynccontextmanager
    async def lifespan(app):
        await scheduler.start()
        yield
        await scheduler.stop()
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None


async def start(background_tasks_factory=None) -> None:
    """
    Launch the periodic scheduler background task.

    background_tasks_factory is not used here (we manage our own tasks),
    but the signature is kept consistent for future dependency injection.
    """
    global _task
    if _task and not _task.done():
        logger.debug("Scheduler already running — skipping duplicate start")
        return
    _task = asyncio.create_task(_scheduler_loop(), name="discovery-scheduler")
    logger.info("Discovery scheduler started")


async def stop() -> None:
    """Cancel the scheduler task. Safe to call if not started."""
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        logger.info("Discovery scheduler stopped")
    _task = None


async def _scheduler_loop() -> None:
    """
    Main scheduler loop.

    Sleeps for `interval_seconds` between runs.
    On each wake: calls bulk_launch_from_keywords with a no-op BackgroundTasks
    shim that schedules jobs as asyncio tasks directly (since we're inside
    a background task, not an HTTP request handler).
    """
    from app.core.config import get_settings
    from app.services.seller_discovery import queue_manager

    settings = get_settings()
    interval = settings.discovery_crawl_interval_hours * 3600  # convert to seconds

    logger.info(
        "Scheduler loop: interval=%.1f hours (%.0f seconds)",
        settings.discovery_crawl_interval_hours, interval,
    )

    # First run: wait a short warmup period so the app is fully ready
    await asyncio.sleep(30)

    while True:
        try:
            logger.info("Scheduler: triggering bulk keyword crawl")
            shim = _BackgroundTasksShim()
            jobs = await queue_manager.bulk_launch_from_keywords(
                shim,
                min_hours_since_crawl=int(settings.discovery_crawl_interval_hours),
            )
            # Flush the shim — all tasks are already dispatched as asyncio tasks
            logger.info("Scheduler: dispatched %d jobs", len(jobs))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Scheduler loop error (will retry next interval): %s", exc)

        await asyncio.sleep(interval)


class _BackgroundTasksShim:
    """
    Minimal shim that mimics FastAPI BackgroundTasks.add_task() inside
    an asyncio background task (where there's no HTTP request context).

    Each added task is wrapped in asyncio.create_task() so it runs
    concurrently and respects the global concurrency semaphore.
    """

    def add_task(self, func, *args, **kwargs) -> None:
        asyncio.create_task(func(*args, **kwargs))
