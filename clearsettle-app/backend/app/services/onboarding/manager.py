"""
Onboarding session manager — CRUD operations for onboarding sessions and steps.

Responsibilities:
  - create_session: initialise a new session with 8 pending steps
  - get_session: load session with steps, events, checkpoints
  - get_progress: compute percentage + current_step summary
  - advance_step: update a step status and emit an event
  - list_sessions: company-scoped listing
  - abandon_session: mark a session as abandoned

Does NOT contain business logic (validation/orchestration) — those live in
validators.py and orchestrator.py.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.onboarding_checkpoint import OnboardingCheckpoint
from app.db.models.onboarding_event import OnboardingEvent
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.onboarding_step import OnboardingStep

logger = logging.getLogger(__name__)

# Ordered step definitions
ONBOARDING_STEPS: list[dict] = [
    {"name": "company_profile",          "order": 1},
    {"name": "marketplace_selection",    "order": 2},
    {"name": "platform_connection",      "order": 3},
    {"name": "credential_verification",  "order": 4},
    {"name": "initial_sync",             "order": 5},
    {"name": "settlement_ingestion",     "order": 6},
    {"name": "reconciliation_activation","order": 7},
    {"name": "dashboard_activation",     "order": 8},
]


async def create_session(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    metadata: Optional[dict] = None,
) -> OnboardingSession:
    """
    Create a new onboarding session and seed all 8 steps as 'pending'.

    Emits a 'session_created' event.  Does not commit — caller commits.
    """
    session = OnboardingSession(
        company_id=company_id,
        platform=platform,
        status="created",
        current_step=ONBOARDING_STEPS[0]["name"],
        metadata_json=json.dumps(metadata or {}),
    )
    db.add(session)
    await db.flush()   # get session.id

    for step_def in ONBOARDING_STEPS:
        db.add(OnboardingStep(
            session_id=session.id,
            step_name=step_def["name"],
            step_order=step_def["order"],
            status="pending",
        ))

    _emit_event(db, session.id, "session_created", description="Onboarding session created")
    return session


async def get_session(db: AsyncSession, session_id: UUID) -> OnboardingSession | None:
    """Load a session with its steps, events, and checkpoints."""
    res = await db.execute(
        select(OnboardingSession)
        .where(OnboardingSession.id == session_id)
        .options(
            selectinload(OnboardingSession.steps),
            selectinload(OnboardingSession.events),
            selectinload(OnboardingSession.checkpoints),
        )
    )
    return res.scalar_one_or_none()


async def list_sessions(
    db: AsyncSession,
    company_id: UUID,
    platform: Optional[str] = None,
    limit: int = 20,
) -> list[OnboardingSession]:
    """List sessions scoped to the company, newest first."""
    q = (
        select(OnboardingSession)
        .where(OnboardingSession.company_id == company_id)
        .options(selectinload(OnboardingSession.steps))
        .order_by(OnboardingSession.created_at.desc())
        .limit(limit)
    )
    if platform:
        q = q.where(OnboardingSession.platform == platform)
    res = await db.execute(q)
    return list(res.scalars().all())


def get_progress(session: OnboardingSession) -> dict[str, Any]:
    """Compute progress summary from an already-loaded session."""
    steps = sorted(session.steps, key=lambda s: s.step_order)
    total = len(steps)
    completed = sum(1 for s in steps if s.status == "completed")
    failed    = sum(1 for s in steps if s.status == "failed")
    pct = round(completed / total * 100) if total else 0

    current = next(
        (s.step_name for s in steps if s.status in ("in_progress", "pending")),
        None,
    )
    return {
        "session_id":         str(session.id),
        "platform":           session.platform,
        "status":             session.status,
        "current_step":       current or session.current_step,
        "steps_total":        total,
        "steps_completed":    completed,
        "steps_failed":       failed,
        "progress_pct":       pct,
        "is_complete":        session.status == "completed",
        "completed_at":       session.completed_at.isoformat() if session.completed_at else None,
        "steps": [
            {
                "step_name":     s.step_name,
                "step_order":    s.step_order,
                "status":        s.status,
                "attempt_count": s.attempt_count,
                "started_at":    s.started_at.isoformat() if s.started_at else None,
                "completed_at":  s.completed_at.isoformat() if s.completed_at else None,
                "error_message": s.error_message,
            }
            for s in steps
        ],
    }


async def advance_step(
    db: AsyncSession,
    session: OnboardingSession,
    step_name: str,
    new_status: str,
    *,
    error_message: Optional[str] = None,
    result_data: Optional[dict] = None,
) -> OnboardingStep:
    """
    Update a step's status and emit the corresponding event.

    Also advances the session status:
      - First in_progress step → session becomes 'in_progress'
      - All steps completed    → session becomes 'completed'
      - Step failed            → session stays 'in_progress' (retry possible)
    """
    # Reload step from the already-loaded steps list
    step = next(
        (s for s in session.steps if s.step_name == step_name),
        None,
    )
    if not step:
        raise ValueError(f"Step '{step_name}' not found in session {session.id}")

    now = datetime.utcnow()
    step.status = new_status
    step.attempt_count = (step.attempt_count or 0) + 1

    if new_status == "in_progress":
        step.started_at = now
    elif new_status in ("completed", "failed", "skipped"):
        step.completed_at = now
        step.error_message = error_message
        if result_data:
            step.result_json = json.dumps(result_data, default=str)

    db.add(step)

    # Update session
    if new_status == "in_progress" and session.status == "created":
        session.status = "in_progress"
    session.current_step = step_name

    if new_status == "completed":
        # Check if all steps are done
        all_done = all(s.status in ("completed", "skipped") for s in session.steps)
        if all_done:
            session.status = "completed"
            session.completed_at = now
            _emit_event(db, session.id, "session_completed",
                        step_name=step_name, description="All onboarding steps completed")

    db.add(session)

    event_type = {
        "in_progress": "step_started",
        "completed":   "step_completed",
        "failed":      "step_failed",
        "skipped":     "step_skipped",
    }.get(new_status, "step_updated")

    _emit_event(db, session.id, event_type, step_name=step_name,
                description=error_message or f"Step {step_name} → {new_status}")
    return step


async def abandon_session(db: AsyncSession, session: OnboardingSession) -> None:
    """Mark session as abandoned and emit an event."""
    session.status = "abandoned"
    db.add(session)
    _emit_event(db, session.id, "session_abandoned", description="Session abandoned by user")


def _emit_event(
    db: AsyncSession,
    session_id: UUID,
    event_type: str,
    *,
    step_name: Optional[str] = None,
    description: Optional[str] = None,
    payload: Optional[dict] = None,
    triggered_by: str = "system",
) -> OnboardingEvent:
    ev = OnboardingEvent(
        session_id=session_id,
        event_type=event_type,
        step_name=step_name,
        description=description,
        payload_json=json.dumps(payload or {}, default=str),
        triggered_by=triggered_by,
    )
    db.add(ev)
    return ev
