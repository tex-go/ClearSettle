"""
Onboarding orchestrator — drives automatic step progression.

After a user manually completes steps 1–4 (profile, marketplace, connection,
credential verification), the orchestrator handles the automated tail:
  step 5: initial_sync       — creates and dispatches a sync job
  step 6: settlement_ingestion — polls until at least one settlement exists
  step 7: reconciliation_activation — triggers a settlements sync job
  step 8: dashboard_activation — verifies KPI data is ready

advance_onboarding() is the main entry point — it determines what can be
auto-advanced and drives the session forward without user intervention.

trigger_initial_sync() and activate_reconciliation() are also callable
directly from the router for manual activation.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.onboarding_session import OnboardingSession
from app.db.models.platform_connection import PlatformConnection
from app.db.models.settlement import Settlement
from app.db.models.sync_job import SyncJob
from app.services.onboarding.manager import advance_step, get_session
from app.services.onboarding.validators import validate_step
from app.services.sync import job_manager, registry

logger = logging.getLogger(__name__)

AUTO_ADVANCE_STEPS = {
    "initial_sync",
    "settlement_ingestion",
    "reconciliation_activation",
    "dashboard_activation",
}


async def _get_connection(
    db: AsyncSession, company_id: UUID, platform: str
) -> PlatformConnection | None:
    res = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company_id,
            PlatformConnection.platform   == platform,
            PlatformConnection.status     == "connected",
        )
    )
    return res.scalar_one_or_none()


async def trigger_initial_sync(
    db: AsyncSession,
    session: OnboardingSession,
    company_id: UUID,
) -> dict:
    """
    Dispatch a settlements sync job for the onboarding session.

    Returns a summary dict with job_id and status.
    """
    conn = await _get_connection(db, company_id, session.platform)
    if not conn:
        return {"status": "error", "message": "No connected platform found"}

    job = await job_manager.create_job(
        db,
        connection_id=conn.id,
        company_id=company_id,
        platform=session.platform,
        job_type="settlements",
        triggered_by="onboarding",
        job_options={"days_back": 90},
    )

    # Update session with the connection link
    session.connection_id = conn.id
    db.add(session)

    # Note: background task dispatch happens in the router via BackgroundTasks
    return {
        "status": "dispatched",
        "job_id": str(job.id),
        "job_type": "settlements",
        "message": "Initial sync job created — ingestion will begin shortly",
    }


async def advance_onboarding(
    db: AsyncSession,
    session_id: UUID,
    company_id: UUID,
) -> dict:
    """
    Attempt to auto-advance the session through any steps that can be
    validated without user input.

    Returns a summary of what was advanced.
    """
    session = await get_session(db, session_id)
    if not session or session.company_id != company_id:
        return {"status": "error", "message": "Session not found"}

    if session.status in ("completed", "abandoned"):
        return {"status": "no_op", "message": f"Session already {session.status}"}

    advanced: list[str] = []
    blocked:  list[dict] = []

    for step in sorted(session.steps, key=lambda s: s.step_order):
        if step.status in ("completed", "skipped"):
            continue
        if step.status == "in_progress":
            blocked.append({"step": step.step_name, "reason": "already in progress"})
            break

        if step.step_name not in AUTO_ADVANCE_STEPS:
            blocked.append({"step": step.step_name, "reason": "requires user action"})
            break

        # Validate the step
        passed, errors = await validate_step(db, company_id, session.platform, step.step_name)
        if passed:
            await advance_step(db, session, step.step_name, "completed")
            advanced.append(step.step_name)
        else:
            blocked.append({"step": step.step_name, "reason": errors[0] if errors else "validation failed"})
            break

    return {
        "status": "ok",
        "session_id": str(session_id),
        "advanced": advanced,
        "blocked_at": blocked[0] if blocked else None,
    }


async def activate_reconciliation(
    db: AsyncSession,
    session: OnboardingSession,
    company_id: UUID,
) -> dict:
    """Trigger a settlement sync job to drive the reconciliation activation step."""
    conn = await _get_connection(db, company_id, session.platform)
    if not conn:
        return {"status": "error", "message": "No connected platform found for reconciliation"}

    # Check if there are any settlements first
    res = await db.execute(
        select(Settlement.id).where(
            Settlement.company_id == company_id,
            Settlement.platform   == session.platform,
        ).limit(1)
    )
    if not res.scalar_one_or_none():
        return {"status": "error", "message": "No settlements available — run initial sync first"}

    job = await job_manager.create_job(
        db,
        connection_id=conn.id,
        company_id=company_id,
        platform=session.platform,
        job_type="settlements",
        triggered_by="onboarding_reconciliation",
        job_options={"days_back": 90},
    )
    return {
        "status": "dispatched",
        "job_id": str(job.id),
        "message": "Reconciliation activation sync triggered",
    }
