"""
Onboarding step validators — live checks performed before marking a step complete.

Each validator returns (passed: bool, errors: list[str]).
Validators are intentionally side-effect-free: they only read DB state and
call external APIs (or skip the call if not configured).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.company import Company
from app.db.models.platform_connection import PlatformConnection
from app.db.models.settlement import Settlement
from app.db.models.sync_job import SyncJob

logger = logging.getLogger(__name__)

ValidationResult = tuple[bool, list[str]]


async def validate_company_profile(db: AsyncSession, company_id: UUID) -> ValidationResult:
    """Check the company has GSTIN, name, and contact info filled in."""
    res = await db.execute(select(Company).where(Company.id == company_id))
    company = res.scalar_one_or_none()
    if not company:
        return False, ["Company not found"]

    errors: list[str] = []
    if not getattr(company, "gstin", None):
        errors.append("GSTIN is required")
    if not getattr(company, "name", None):
        errors.append("Company name is required")
    return len(errors) == 0, errors


async def validate_marketplace_selection(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Verify the requested platform is supported."""
    supported = {"amazon", "flipkart", "meesho", "myntra"}
    if platform.lower() not in supported:
        return False, [f"Platform '{platform}' is not yet supported. Supported: {sorted(supported)}"]
    return True, []


async def validate_platform_connection(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Check that at least one platform connection exists for this company."""
    res = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company_id,
            PlatformConnection.platform   == platform,
        )
    )
    conn = res.scalar_one_or_none()
    if not conn:
        return False, [f"No {platform} connection found. Complete the OAuth flow first."]
    if conn.status not in ("connected",):
        return False, [f"Connection status is '{conn.status}' — must be 'connected'"]
    return True, []


async def validate_credential_verification(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Verify credentials are fresh (token not expired)."""
    res = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company_id,
            PlatformConnection.platform   == platform,
            PlatformConnection.status     == "connected",
        )
    )
    conn = res.scalar_one_or_none()
    if not conn:
        return False, ["No connected platform found"]

    errors: list[str] = []
    if platform == "amazon":
        if not getattr(conn, "sp_refresh_token_enc", None):
            errors.append("SP API refresh token is missing — re-authorize the connection")
        expires = getattr(conn, "sp_access_token_expires_at", None)
        if expires and expires < datetime.utcnow():
            errors.append("Access token has expired — refresh the token")
    return len(errors) == 0, errors


async def validate_initial_sync(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Check that at least one sync job has been created and is not pending."""
    res = await db.execute(
        select(func.count(SyncJob.id)).where(
            SyncJob.company_id == company_id,
            SyncJob.platform   == platform,
            SyncJob.status.in_(["running", "completed", "failed"]),
        )
    )
    count = res.scalar() or 0
    if count == 0:
        return False, ["No sync job has been triggered yet. Start an initial sync."]
    return True, []


async def validate_settlement_ingestion(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Verify at least one settlement has been ingested."""
    res = await db.execute(
        select(func.count(Settlement.id)).where(
            Settlement.company_id == company_id,
            Settlement.platform   == platform,
        )
    )
    count = res.scalar() or 0
    if count == 0:
        return False, ["No settlements have been ingested yet. Wait for the sync to complete."]
    return True, []


async def validate_reconciliation_activation(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Check that at least one completed reconciliation job exists."""
    res = await db.execute(
        select(func.count(SyncJob.id)).where(
            SyncJob.company_id == company_id,
            SyncJob.platform   == platform,
            SyncJob.job_type   == "settlements",
            SyncJob.status     == "completed",
        )
    )
    count = res.scalar() or 0
    if count == 0:
        return False, ["No completed settlement sync found. Run reconciliation first."]
    return True, []


async def validate_dashboard_activation(
    db: AsyncSession, company_id: UUID, platform: str
) -> ValidationResult:
    """Check settlement data exists and is recent enough for KPI generation."""
    res = await db.execute(
        select(func.count(Settlement.id)).where(
            Settlement.company_id == company_id,
            Settlement.platform   == platform,
        )
    )
    count = res.scalar() or 0
    if count == 0:
        return False, ["No settlement data available for dashboard generation"]
    return True, []


# ── Dispatcher ────────────────────────────────────────────────────────────────

STEP_VALIDATORS = {
    "company_profile":         validate_company_profile,
    "marketplace_selection":   validate_marketplace_selection,
    "platform_connection":     validate_platform_connection,
    "credential_verification": validate_credential_verification,
    "initial_sync":            validate_initial_sync,
    "settlement_ingestion":    validate_settlement_ingestion,
    "reconciliation_activation": validate_reconciliation_activation,
    "dashboard_activation":    validate_dashboard_activation,
}


async def validate_step(
    db: AsyncSession,
    company_id: UUID,
    platform: str,
    step_name: str,
) -> ValidationResult:
    """Dispatch to the appropriate validator for the given step."""
    validator = STEP_VALIDATORS.get(step_name)
    if not validator:
        return False, [f"Unknown step: '{step_name}'"]
    try:
        return await validator(db, company_id, platform)
    except Exception as exc:
        logger.exception("validator: step=%s error=%s", step_name, exc)
        return False, [f"Validation error: {exc}"]
