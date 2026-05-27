"""
Onboarding checkpoint persistence — save/load step state for safe retry/resume.

A checkpoint is upserted using a DELETE + INSERT pattern (no ON CONFLICT support
needed — the unique constraint on session_id + step_name guards integrity).
"""
from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.onboarding_checkpoint import OnboardingCheckpoint

logger = logging.getLogger(__name__)


async def save_checkpoint(
    db: AsyncSession,
    session_id: UUID,
    step_name: str,
    data: dict[str, Any],
) -> OnboardingCheckpoint:
    """Upsert a checkpoint for (session_id, step_name)."""
    # Delete existing checkpoint for this step
    await db.execute(
        delete(OnboardingCheckpoint).where(
            OnboardingCheckpoint.session_id == session_id,
            OnboardingCheckpoint.step_name == step_name,
        )
    )
    cp = OnboardingCheckpoint(
        session_id=session_id,
        step_name=step_name,
        data_json=json.dumps(data, default=str),
    )
    db.add(cp)
    await db.flush()
    logger.debug("checkpoint saved: session=%s step=%s", session_id, step_name)
    return cp


async def load_checkpoint(
    db: AsyncSession,
    session_id: UUID,
    step_name: str,
) -> dict[str, Any] | None:
    """Return the checkpoint data dict, or None if no checkpoint exists."""
    res = await db.execute(
        select(OnboardingCheckpoint).where(
            OnboardingCheckpoint.session_id == session_id,
            OnboardingCheckpoint.step_name == step_name,
        )
    )
    cp = res.scalar_one_or_none()
    if not cp:
        return None
    try:
        return json.loads(cp.data_json)
    except Exception:
        return {}


async def clear_checkpoints(db: AsyncSession, session_id: UUID) -> int:
    """Delete all checkpoints for a session. Returns count deleted."""
    result = await db.execute(
        delete(OnboardingCheckpoint).where(
            OnboardingCheckpoint.session_id == session_id
        )
    )
    return result.rowcount
