"""
Job type → orchestrator handler registry.

This is the single source of truth for supported job types.

Future Celery migration
-----------------------
When adding Celery, replace the body of `dispatch` with:
    celery_app.send_task(f"sync.{job_type}", args=[job_id])

Keep HANDLERS and VALID_JOB_TYPES as documentation of available task names.
"""
import logging
from collections.abc import Callable

from app.services.sync.orchestrator import run_orders_sync, run_settlements_sync

logger = logging.getLogger(__name__)

HANDLERS: dict[str, Callable[[str], None]] = {
    "orders":      run_orders_sync,
    "settlements": run_settlements_sync,
}

VALID_JOB_TYPES: frozenset[str] = frozenset(HANDLERS.keys())


async def dispatch(job_type: str, job_id: str) -> None:
    """
    Route a job to its handler.

    Currently executes inline within the FastAPI background task.
    Future: submit to Celery/Redis queue instead of direct invocation.
    """
    handler = HANDLERS.get(job_type)
    if handler is None:
        logger.error("dispatch: unknown job_type %r for job %s", job_type, job_id)
        return
    logger.info("Dispatching job %s type=%s", job_id, job_type)
    await handler(job_id)
