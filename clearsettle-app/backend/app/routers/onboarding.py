"""
Platform onboarding router — multi-step seller activation flow.

Endpoints
---------
POST   /onboarding/sessions                         — start a new onboarding session
GET    /onboarding/sessions                         — list sessions for the company
GET    /onboarding/sessions/{session_id}            — session detail with step progress
GET    /onboarding/sessions/{session_id}/progress   — progress summary (percentage)
POST   /onboarding/sessions/{session_id}/steps/{step}/complete  — mark step complete
POST   /onboarding/sessions/{session_id}/steps/{step}/retry     — retry a failed step
POST   /onboarding/sessions/{session_id}/validate/{step}        — validate step readiness
POST   /onboarding/sessions/{session_id}/activate               — trigger sync pipeline
POST   /onboarding/sessions/{session_id}/advance                — auto-advance eligible steps
DELETE /onboarding/sessions/{session_id}                        — abandon a session
GET    /onboarding/analytics                                     — onboarding funnel stats
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.rbac import require_db_permission
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.user import User
from app.services.onboarding.manager import (
    ONBOARDING_STEPS, abandon_session, advance_step,
    create_session, get_progress, get_session, list_sessions,
)
from app.services.onboarding.orchestrator import (
    activate_reconciliation, advance_onboarding, trigger_initial_sync,
)
from app.services.onboarding.validators import validate_step
from app.services.sync import registry

logger = logging.getLogger(__name__)
router = APIRouter()

SUPPORTED_PLATFORMS = {"amazon", "flipkart", "meesho", "myntra"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _company(user: User):
    c = user.companies[0] if getattr(user, "companies", None) else None
    if not c:
        raise HTTPException(status_code=400, detail="No company found for this user")
    return c


async def _get_session_owned(
    db: AsyncSession, session_id: str, company_id: UUID
) -> OnboardingSession:
    session = await get_session(db, UUID(session_id))
    if not session or session.company_id != company_id:
        raise HTTPException(status_code=404, detail="Onboarding session not found")
    return session


def _ser_session(s: OnboardingSession) -> dict:
    steps = sorted(s.steps or [], key=lambda x: x.step_order)
    return {
        "id":            str(s.id),
        "company_id":    str(s.company_id),
        "platform":      s.platform,
        "status":        s.status,
        "current_step":  s.current_step,
        "connection_id": str(s.connection_id) if s.connection_id else None,
        "completed_at":  s.completed_at.isoformat() if s.completed_at else None,
        "created_at":    s.created_at.isoformat() if s.created_at else None,
        "steps": [
            {
                "step_name":     step.step_name,
                "step_order":    step.step_order,
                "status":        step.status,
                "attempt_count": step.attempt_count,
                "started_at":    step.started_at.isoformat()   if step.started_at   else None,
                "completed_at":  step.completed_at.isoformat() if step.completed_at else None,
                "error_message": step.error_message,
            }
            for step in steps
        ],
    }


# ── Create session ────────────────────────────────────────────────────────────

@router.post("/sessions", status_code=201)
async def create_onboarding_session(
    platform: str = Query(default="amazon"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    """Start a new onboarding session for the authenticated company."""
    if platform.lower() not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' not supported. Supported: {sorted(SUPPORTED_PLATFORMS)}",
        )
    company = _company(current_user)
    session = await create_session(db, company.id, platform)
    await db.commit()
    await db.refresh(session)
    session = await get_session(db, session.id)
    return _ser_session(session)


# ── List sessions ─────────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_onboarding_sessions(
    platform: Optional[str] = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:read")),
):
    company = _company(current_user)
    sessions = await list_sessions(db, company.id, platform=platform, limit=limit)
    return [_ser_session(s) for s in sessions]


# ── Session detail ────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}")
async def get_onboarding_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:read")),
):
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)
    return _ser_session(session)


# ── Progress summary ──────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/progress")
async def get_onboarding_progress(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:read")),
):
    """Return a percentage-based progress summary with step statuses."""
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)
    return get_progress(session)


# ── Complete a step ───────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/steps/{step_name}/complete")
async def complete_step(
    session_id: str,
    step_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    """Mark a step as completed after the user has confirmed it."""
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)

    valid_steps = {s["name"] for s in ONBOARDING_STEPS}
    if step_name not in valid_steps:
        raise HTTPException(status_code=400, detail=f"Unknown step: '{step_name}'")

    await advance_step(db, session, step_name, "completed")
    await db.commit()
    return {"session_id": session_id, "step": step_name, "status": "completed"}


# ── Retry a failed step ───────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/steps/{step_name}/retry")
async def retry_step(
    session_id: str,
    step_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    """Reset a failed or stuck step back to 'pending' for a fresh attempt."""
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)

    step = next((s for s in session.steps if s.step_name == step_name), None)
    if not step:
        raise HTTPException(status_code=404, detail=f"Step '{step_name}' not found")
    if step.status not in ("failed", "in_progress"):
        raise HTTPException(
            status_code=400,
            detail=f"Only failed or stuck steps can be retried (current: '{step.status}')",
        )

    step.status = "pending"
    step.error_message = None
    step.started_at = None
    step.completed_at = None
    db.add(step)
    await db.commit()
    return {"session_id": session_id, "step": step_name, "status": "pending", "message": "Step reset for retry"}


# ── Validate a step ───────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/validate/{step_name}")
async def validate_onboarding_step(
    session_id: str,
    step_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:read")),
):
    """Run the validator for a step and return pass/fail with error details."""
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)
    passed, errors = await validate_step(db, company.id, session.platform, step_name)
    return {
        "session_id": session_id,
        "step": step_name,
        "passed": passed,
        "errors": errors,
    }


# ── Activate (trigger sync pipeline) ─────────────────────────────────────────

@router.post("/sessions/{session_id}/activate")
async def activate_onboarding(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    """
    Trigger the automated activation tail of the onboarding flow.

    Dispatches an initial settlements sync job. The background job will ingest
    settlements, after which reconciliation can be activated.
    """
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)

    if session.status == "completed":
        return {"status": "already_complete", "session_id": session_id}

    result = await trigger_initial_sync(db, session, company.id)
    if result["status"] == "dispatched":
        # Mark initial_sync as in_progress
        await advance_step(db, session, "initial_sync", "in_progress")
        background_tasks.add_task(registry.dispatch, "settlements", result["job_id"])

    await db.commit()
    return {"session_id": session_id, **result}


# ── Auto-advance eligible steps ───────────────────────────────────────────────

@router.post("/sessions/{session_id}/advance")
async def auto_advance(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    """
    Automatically advance any steps whose validation conditions are already met.

    Useful for polling after an async operation (sync job) completes.
    """
    company = _company(current_user)
    result = await advance_onboarding(db, UUID(session_id), company.id)
    await db.commit()
    return result


# ── Abandon session ───────────────────────────────────────────────────────────

@router.delete("/sessions/{session_id}")
async def abandon_onboarding_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("platforms:write")),
):
    company = _company(current_user)
    session = await _get_session_owned(db, session_id, company.id)
    if session.status in ("completed", "abandoned"):
        raise HTTPException(
            status_code=400,
            detail=f"Session is already '{session.status}' — cannot abandon",
        )
    await abandon_session(db, session)
    await db.commit()
    return {"session_id": session_id, "status": "abandoned"}


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
async def onboarding_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_db_permission("analytics:read")),
):
    """Onboarding funnel metrics across all company sessions."""
    company = _company(current_user)

    res = await db.execute(
        select(
            OnboardingSession.status,
            OnboardingSession.platform,
            func.count(OnboardingSession.id).label("count"),
        )
        .where(OnboardingSession.company_id == company.id)
        .group_by(OnboardingSession.status, OnboardingSession.platform)
    )
    rows = res.all()

    by_status: dict = {}
    by_platform: dict = {}
    total = 0
    for status, platform, count in rows:
        by_status[status] = by_status.get(status, 0) + count
        by_platform[platform] = by_platform.get(platform, 0) + count
        total += count

    return {
        "total_sessions":  total,
        "by_status":       by_status,
        "by_platform":     by_platform,
        "completion_rate": round(by_status.get("completed", 0) / total * 100, 1) if total else 0,
        "step_definitions": ONBOARDING_STEPS,
    }
