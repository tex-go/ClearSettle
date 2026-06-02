"""
TokenManagementService — handles access token refresh across providers.

The access token refresh buffer (default 5 min) is configurable via
MARKETPLACE_ACCESS_TOKEN_REFRESH_BUFFER_M in the environment.
"""
from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.db.models.marketplace_connection import (
    MarketplaceConnection,
    MarketplaceCredentials,
)
from app.services.marketplace import audit_service
from app.services.marketplace.audit_service import AuditAction

logger = logging.getLogger(__name__)


def _buffer_minutes() -> int:
    return get_settings().marketplace_access_token_refresh_buffer_m


async def ensure_valid_token(
    connection_id: UUID,
    db:            AsyncSession,
) -> str:
    """
    Return a valid access token for the given connection.
    Automatically refreshes if the token is within the expiry buffer.
    Commits the refresh to DB before returning.
    """
    from app.services.marketplace.provider_registry import get_provider

    conn = (await db.execute(
        select(MarketplaceConnection)
        .where(
            MarketplaceConnection.id == connection_id,
            MarketplaceConnection.deleted_at.is_(None),
        )
        .options(
            selectinload(MarketplaceConnection.marketplace),
            selectinload(MarketplaceConnection.credentials),
        )
    )).scalar_one_or_none()

    if conn is None:
        raise ValueError(f"Connection {connection_id} not found.")
    if conn.credentials is None:
        raise ValueError(f"No credentials stored for connection {connection_id}.")

    provider = get_provider(conn.marketplace.slug)

    if provider.needs_token_refresh(conn.credentials, buffer_minutes=_buffer_minutes()):
        logger.info(
            "Access token expiring soon for connection %s (%s) — refreshing.",
            connection_id, conn.marketplace.slug
        )
        tokens = await provider.refresh_tokens(conn, conn.credentials)
        provider.store_oauth_tokens(conn.credentials, tokens)

        await audit_service.record(
            db, AuditAction.OAUTH_REFRESH,
            company_id    = conn.company_id,
            connection_id = conn.id,
            new_value     = {"expires_at": conn.credentials.access_token_expires_at.isoformat()
                             if conn.credentials.access_token_expires_at else None},
        )
        await db.commit()

    return provider.get_access_token(conn.credentials)
