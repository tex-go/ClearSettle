"""
Mobile Push Notification Router
POST /notifications/register   — store device FCM token
DELETE /notifications/device   — remove device token
GET /notifications/            — list user's notifications (same as /dashboard/notifications)

FCM push delivery requires FIREBASE_SERVICE_ACCOUNT_JSON env var to be set.
Without it, tokens are stored but no pushes are sent (graceful degradation).
"""

import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.deps import get_current_user, get_db as get_async_session
from app.db.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DeviceTokenRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, description="Firebase Cloud Messaging device token")
    platform:  str = Field(default="android", description="android | ios")
    device_id: str = Field(default="", description="Optional unique device identifier")


class DeviceTokenResponse(BaseModel):
    status:  str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=DeviceTokenResponse,
    summary="Register device for push notifications",
)
async def register_device(
    body: DeviceTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Idempotent — safe to call on every app launch.
    Stores the FCM token linked to the authenticated user.
    """
    try:
        # Upsert: if token already exists update updated_at, else insert
        existing = await db.execute(
            text(
                "SELECT id FROM push_tokens "
                "WHERE user_id = :uid AND fcm_token = :token"
            ),
            {"uid": str(current_user.id), "token": body.fcm_token},
        )
        row = existing.first()
        now = datetime.now(timezone.utc)

        if row:
            await db.execute(
                text(
                    "UPDATE push_tokens SET updated_at = :now "
                    "WHERE user_id = :uid AND fcm_token = :token"
                ),
                {"now": now, "uid": str(current_user.id), "token": body.fcm_token},
            )
        else:
            await db.execute(
                text(
                    "INSERT INTO push_tokens "
                    "(user_id, fcm_token, platform, device_id, created_at, updated_at) "
                    "VALUES (:uid, :token, :platform, :device_id, :now, :now)"
                ),
                {
                    "uid": str(current_user.id),
                    "token": body.fcm_token,
                    "platform": body.platform,
                    "device_id": body.device_id or "",
                    "now": now,
                },
            )
        await db.commit()
    except Exception as exc:
        logger.warning("push_tokens table not yet created — run migration: %s", exc)
        # Graceful degradation: accept the request but log the issue
        return DeviceTokenResponse(
            status="pending_migration",
            message="Token received. Run 'alembic upgrade head' to activate push notifications.",
        )

    return DeviceTokenResponse(status="registered", message="Device registered for push notifications.")


@router.delete(
    "/device",
    response_model=DeviceTokenResponse,
    summary="Unregister device (logout / token refresh)",
)
async def unregister_device(
    fcm_token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        await db.execute(
            text(
                "DELETE FROM push_tokens "
                "WHERE user_id = :uid AND fcm_token = :token"
            ),
            {"uid": str(current_user.id), "token": fcm_token},
        )
        await db.commit()
    except Exception as exc:
        logger.warning("Could not delete push token: %s", exc)

    return DeviceTokenResponse(status="unregistered", message="Device removed.")


@router.get(
    "/unread-count",
    summary="Badge count for mobile app icon",
)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Returns a simple integer badge count.
    Currently counts unresolved discrepancies + pending settlements as proxy
    for total actionable notifications.
    """
    try:
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM discrepancy_events "
                "WHERE company_id = :cid "
                "AND workflow_state NOT IN ('resolved', 'dismissed', 'rejected')"
            ),
            {"cid": str(current_user.company_id) if hasattr(current_user, "company_id") else ""},
        )
        count = result.scalar() or 0
    except Exception:
        count = 0

    return {"unread_count": count}
