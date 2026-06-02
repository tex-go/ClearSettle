"""
MarketplaceAuditService — write immutable audit records.

Every significant marketplace action (connect, disconnect, sync, credential update)
is recorded here. Audit logs are append-only; never deleted via application code.

The caller passes an open AsyncSession. This service does NOT commit.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketplace_connection import MarketplaceAuditLog

logger = logging.getLogger(__name__)

# ── Action constants ───────────────────────────────────────────────────────────

class AuditAction:
    CONNECTION_CREATED      = "connection.created"
    CONNECTION_CONNECTED    = "connection.connected"
    CONNECTION_DISCONNECTED = "connection.disconnected"
    CONNECTION_ERROR        = "connection.error"
    CREDENTIAL_UPDATED      = "credential.updated"
    OAUTH_INITIATED         = "oauth.initiated"
    OAUTH_CALLBACK          = "oauth.callback"
    OAUTH_REFRESH           = "oauth.token_refreshed"
    SYNC_STARTED            = "sync.started"
    SYNC_COMPLETED          = "sync.completed"
    SYNC_FAILED             = "sync.failed"
    ACCOUNT_FETCHED         = "account.fetched"
    CONNECTION_VALIDATED    = "connection.validated"


async def record(
    db:            AsyncSession,
    action:        str,
    company_id:    UUID,
    *,
    connection_id: Optional[UUID] = None,
    performed_by:  Optional[UUID] = None,
    old_value:     Optional[dict[str, Any]] = None,
    new_value:     Optional[dict[str, Any]] = None,
    ip_address:    Optional[str] = None,
    user_agent:    Optional[str] = None,
) -> MarketplaceAuditLog:
    """
    Append an audit record to marketplace_audit_logs.
    Returns the ORM instance (not yet committed).
    """
    entry = MarketplaceAuditLog(
        company_id    = company_id,
        connection_id = connection_id,
        performed_by  = performed_by,
        action        = action,
        old_value     = old_value,
        new_value     = new_value,
        ip_address    = ip_address,
        user_agent    = user_agent,
        created_at    = datetime.utcnow(),
    )
    db.add(entry)
    logger.debug("Audit: %s (company=%s connection=%s)", action, company_id, connection_id)
    return entry
