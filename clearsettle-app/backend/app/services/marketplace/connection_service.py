"""
MarketplaceConnectionService — CRUD for marketplace connections.

Responsibilities
----------------
- Create / read / update / soft-delete MarketplaceConnection rows
- Create / update MarketplaceCredentials rows (never return plaintext)
- Dispatch to the correct provider for connecting and disconnecting
- All DB writes are NOT committed here — caller commits

All functions accept an open AsyncSession.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.marketplace_connection import (
    Marketplace,
    MarketplaceAccount,
    MarketplaceConnection,
    MarketplaceCredentials,
)
from app.services.marketplace import audit_service
from app.services.marketplace.abstract_provider import (
    AccountDetails,
    ConnectionStatus,
    ConnectionType,
)
from app.services.marketplace.audit_service import AuditAction

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_marketplace(slug: str, db: AsyncSession) -> Marketplace:
    row = (await db.execute(
        select(Marketplace).where(Marketplace.slug == slug, Marketplace.is_active.is_(True))
    )).scalar_one_or_none()
    if row is None:
        raise ValueError(f"Marketplace '{slug}' not found or inactive.")
    return row


async def _get_connection(
    company_id:    UUID,
    marketplace_id: UUID,
    db:            AsyncSession,
    *,
    include_credentials: bool = False,
) -> Optional[MarketplaceConnection]:
    stmt = (
        select(MarketplaceConnection)
        .where(
            MarketplaceConnection.company_id    == company_id,
            MarketplaceConnection.marketplace_id == marketplace_id,
            MarketplaceConnection.deleted_at.is_(None),
        )
        .options(selectinload(MarketplaceConnection.marketplace))
    )
    if include_credentials:
        stmt = stmt.options(selectinload(MarketplaceConnection.credentials))
    return (await db.execute(stmt)).scalar_one_or_none()


async def _get_or_create_connection(
    company_id:    UUID,
    marketplace_id: UUID,
    connection_type: str,
    db:            AsyncSession,
) -> tuple[MarketplaceConnection, bool]:
    """Return (connection, created). Does not commit."""
    conn = await _get_connection(company_id, marketplace_id, db)
    if conn:
        return conn, False
    conn = MarketplaceConnection(
        company_id      = company_id,
        marketplace_id  = marketplace_id,
        connection_type = connection_type,
        status          = ConnectionStatus.DISCONNECTED,
    )
    db.add(conn)
    await db.flush()  # assign ID without committing
    return conn, True


async def _get_or_create_credentials(
    connection_id: UUID,
    db:            AsyncSession,
) -> MarketplaceCredentials:
    creds = (await db.execute(
        select(MarketplaceCredentials)
        .where(MarketplaceCredentials.connection_id == connection_id)
    )).scalar_one_or_none()
    if creds is None:
        creds = MarketplaceCredentials(connection_id=connection_id)
        db.add(creds)
        await db.flush()
    return creds


# ── Public API ────────────────────────────────────────────────────────────────

async def list_connections(
    company_id: UUID,
    db:         AsyncSession,
    *,
    include_deleted: bool = False,
) -> list[MarketplaceConnection]:
    """Return all marketplace connections for a company."""
    stmt = (
        select(MarketplaceConnection)
        .where(MarketplaceConnection.company_id == company_id)
        .options(
            selectinload(MarketplaceConnection.marketplace),
            selectinload(MarketplaceConnection.credentials),
            selectinload(MarketplaceConnection.account),
        )
        .order_by(MarketplaceConnection.created_at.desc())
    )
    if not include_deleted:
        stmt = stmt.where(MarketplaceConnection.deleted_at.is_(None))
    return list((await db.execute(stmt)).scalars().all())


async def get_connection_by_id(
    connection_id: UUID,
    company_id:    UUID,
    db:            AsyncSession,
) -> MarketplaceConnection:
    conn = (await db.execute(
        select(MarketplaceConnection)
        .where(
            MarketplaceConnection.id         == connection_id,
            MarketplaceConnection.company_id == company_id,
            MarketplaceConnection.deleted_at.is_(None),
        )
        .options(
            selectinload(MarketplaceConnection.marketplace),
            selectinload(MarketplaceConnection.credentials),
            selectinload(MarketplaceConnection.account),
        )
    )).scalar_one_or_none()
    if conn is None:
        raise ValueError(f"Connection {connection_id} not found.")
    return conn


async def create_manual_connection(
    company_id:      UUID,
    marketplace_slug: str,
    db:              AsyncSession,
    *,
    display_name:    Optional[str] = None,
    performed_by:    Optional[UUID] = None,
    ip_address:      Optional[str] = None,
) -> MarketplaceConnection:
    """
    Create a connection row for a manual-upload marketplace.
    Status is set to 'connected' immediately (no auth handshake needed).
    """
    market = await _get_marketplace(marketplace_slug, db)
    conn, created = await _get_or_create_connection(
        company_id, market.id, ConnectionType.MANUAL_UPLOAD, db
    )
    conn.status       = ConnectionStatus.CONNECTED
    conn.display_name = display_name or market.name
    conn.connected_at = datetime.utcnow()

    await audit_service.record(
        db, AuditAction.CONNECTION_CREATED if created else AuditAction.CONNECTION_CONNECTED,
        company_id    = company_id,
        connection_id = conn.id,
        performed_by  = performed_by,
        new_value     = {"marketplace": marketplace_slug, "type": "manual_upload"},
        ip_address    = ip_address,
    )
    return conn


async def create_credential_connection(
    company_id:       UUID,
    marketplace_slug: str,
    raw_credentials:  dict[str, str],
    db:               AsyncSession,
    *,
    display_name:     Optional[str] = None,
    performed_by:     Optional[UUID] = None,
    ip_address:       Optional[str] = None,
) -> MarketplaceConnection:
    """
    Store API-key/secret credentials and mark the connection active.
    Calls provider.handle_credential_connect() for validation.
    """
    from app.services.marketplace.provider_registry import get_provider
    market   = await _get_marketplace(marketplace_slug, db)
    provider = get_provider(marketplace_slug)

    conn, created = await _get_or_create_connection(
        company_id, market.id, provider.connection_type, db
    )
    conn.status       = ConnectionStatus.CONNECTING
    conn.display_name = display_name or market.name
    await db.flush()

    creds = await _get_or_create_credentials(conn.id, db)

    # Provider validates and stores encrypted credentials
    await provider.handle_credential_connect(raw_credentials, conn, creds)

    conn.status       = ConnectionStatus.CONNECTED
    conn.connected_at = datetime.utcnow()

    await audit_service.record(
        db, AuditAction.CONNECTION_CONNECTED,
        company_id    = company_id,
        connection_id = conn.id,
        performed_by  = performed_by,
        new_value     = {"marketplace": marketplace_slug},
        ip_address    = ip_address,
    )
    return conn


async def disconnect(
    company_id:       UUID,
    marketplace_slug: str,
    db:               AsyncSession,
    *,
    performed_by:     Optional[UUID] = None,
    ip_address:       Optional[str] = None,
) -> MarketplaceConnection:
    """
    Revoke the connection: calls provider.disconnect(), clears credentials,
    soft-deletes the connection row.
    """
    from app.services.marketplace.provider_registry import get_provider, is_supported
    market = await _get_marketplace(marketplace_slug, db)

    conn = await _get_connection(company_id, market.id, db, include_credentials=True)
    if conn is None:
        raise ValueError(f"No active connection to {marketplace_slug}.")

    if is_supported(marketplace_slug) and conn.credentials:
        try:
            provider = get_provider(marketplace_slug)
            await provider.disconnect(conn, conn.credentials)
        except Exception as exc:
            logger.warning("Provider.disconnect() failed for %s: %s", marketplace_slug, exc)

    # Clear credentials
    if conn.credentials:
        creds = conn.credentials
        for field in [
            "access_token_enc", "refresh_token_enc", "client_id_enc",
            "client_secret_enc", "api_key_enc", "api_secret_enc",
            "username_enc", "password_enc", "extra_enc",
            "api_key_display", "scope",
        ]:
            setattr(creds, field, None)
        creds.access_token_expires_at  = None
        creds.refresh_token_expires_at = None

    conn.status          = ConnectionStatus.DISCONNECTED
    conn.disconnected_at = datetime.utcnow()
    conn.deleted_at      = datetime.utcnow()

    await audit_service.record(
        db, AuditAction.CONNECTION_DISCONNECTED,
        company_id    = company_id,
        connection_id = conn.id,
        performed_by  = performed_by,
        ip_address    = ip_address,
    )
    return conn


async def persist_account_details(
    connection_id: UUID,
    details:       AccountDetails,
    db:            AsyncSession,
) -> MarketplaceAccount:
    """Upsert marketplace account info fetched after successful auth."""
    acct = (await db.execute(
        select(MarketplaceAccount)
        .where(MarketplaceAccount.connection_id == connection_id)
    )).scalar_one_or_none()

    if acct is None:
        acct = MarketplaceAccount(connection_id=connection_id)
        db.add(acct)

    acct.account_id       = details.account_id
    acct.account_name     = details.account_name
    acct.account_email    = details.account_email
    acct.account_type     = details.account_type
    acct.region           = details.region
    acct.country          = details.country
    acct.currency         = details.currency
    acct.marketplace_data = details.raw
    acct.last_verified_at = datetime.utcnow()
    return acct
