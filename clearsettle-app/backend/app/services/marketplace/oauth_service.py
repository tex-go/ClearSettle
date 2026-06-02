"""
OAuthService — manages the OAuth 2.0 Authorization Code flow.

Responsibilities
----------------
1. create_oauth_state()     — generate a CSRF-protected state, persist to DB
2. get_authorization_url()  — call provider.get_authorization_url()
3. handle_callback()        — validate state, exchange code, store tokens
4. cleanup_expired_states() — housekeeping (call from a cron or on startup)

None of these functions commit — the caller is responsible.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.marketplace_connection import (
    Marketplace,
    MarketplaceConnection,
    MarketplaceCredentials,
    OAuthState,
)
from app.services.marketplace import audit_service
from app.services.marketplace.abstract_provider import (
    ConnectionStatus,
    OAuthTokens,
)
from app.services.marketplace.audit_service import AuditAction
from app.services.marketplace.connection_service import (
    _get_marketplace,
    _get_or_create_connection,
    _get_or_create_credentials,
    persist_account_details,
)

logger = logging.getLogger(__name__)


def _state_ttl_minutes() -> int:
    return get_settings().marketplace_oauth_state_ttl_minutes


# ── State management ──────────────────────────────────────────────────────────

async def create_oauth_state(
    company_id:       UUID,
    marketplace_slug: str,
    db:               AsyncSession,
    *,
    redirect_uri:     Optional[str] = None,
    extra_params:     Optional[dict] = None,
) -> tuple[OAuthState, str]:
    """
    Generate a cryptographically random state token, persist it, and
    return (OAuthState row, authorization_url).
    """
    from app.services.marketplace.provider_registry import get_provider
    market   = await _get_marketplace(marketplace_slug, db)
    provider = get_provider(marketplace_slug)

    state_token = secrets.token_urlsafe(32)
    expires_at  = datetime.utcnow() + timedelta(minutes=_state_ttl_minutes())

    state_row = OAuthState(
        company_id     = company_id,
        marketplace_id = market.id,
        state_token    = state_token,
        redirect_uri   = redirect_uri,
        extra_params   = extra_params,
        expires_at     = expires_at,
        created_at     = datetime.utcnow(),
    )
    db.add(state_row)
    await db.flush()

    # Create (or fetch) the connection row so the provider can reference it
    conn, _ = await _get_or_create_connection(
        company_id, market.id, provider.connection_type, db
    )
    conn.status = ConnectionStatus.CONNECTING
    await db.flush()

    auth_url = await provider.get_authorization_url(
        state       = state_token,
        redirect_uri = redirect_uri or "",
        connection  = conn,
        shop_domain = extra_params.get("shop_domain") if extra_params else None,
    )

    await audit_service.record(
        db, AuditAction.OAUTH_INITIATED,
        company_id    = company_id,
        connection_id = conn.id,
        new_value     = {"marketplace": marketplace_slug},
    )

    return state_row, auth_url


async def handle_oauth_callback(
    code:             str,
    state_token:      str,
    db:               AsyncSession,
    *,
    shop:             Optional[str] = None,
    ip_address:       Optional[str] = None,
    performed_by:     Optional[UUID] = None,
) -> MarketplaceConnection:
    """
    Validate the CSRF state token, exchange the code for tokens,
    fetch account details, and update the connection to 'connected'.
    """
    from app.services.marketplace.provider_registry import get_provider

    # ── Validate state ─────────────────────────────────────────────────────────
    state_row = (await db.execute(
        select(OAuthState)
        .where(
            OAuthState.state_token == state_token,
            OAuthState.used_at.is_(None),
            OAuthState.expires_at > datetime.utcnow(),
        )
    )).scalar_one_or_none()

    if state_row is None:
        raise ValueError(
            "Invalid or expired OAuth state token. "
            "The authorization may have timed out — please try connecting again."
        )

    # Mark state as used (prevents replay)
    state_row.used_at = datetime.utcnow()

    company_id    = state_row.company_id
    marketplace_id = state_row.marketplace_id

    # ── Load market + provider ─────────────────────────────────────────────────
    market = (await db.execute(
        select(Marketplace).where(Marketplace.id == marketplace_id)
    )).scalar_one()
    provider = get_provider(market.slug)

    # ── Load connection + credentials ──────────────────────────────────────────
    from sqlalchemy.orm import selectinload
    conn = (await db.execute(
        select(MarketplaceConnection)
        .where(
            MarketplaceConnection.company_id    == company_id,
            MarketplaceConnection.marketplace_id == marketplace_id,
            MarketplaceConnection.deleted_at.is_(None),
        )
        .options(selectinload(MarketplaceConnection.marketplace))
    )).scalar_one_or_none()

    if conn is None:
        raise ValueError("Connection row not found. OAuth state may be stale.")

    if shop:
        conn.shop_domain = shop

    creds = await _get_or_create_credentials(conn.id, db)

    # ── Exchange code for tokens ───────────────────────────────────────────────
    tokens: OAuthTokens = await provider.handle_callback(
        code        = code,
        connection  = conn,
        credentials = creds,
        shop        = shop,
    )
    provider.store_oauth_tokens(creds, tokens)

    # ── Fetch seller account details ───────────────────────────────────────────
    try:
        account = await provider.get_account_details(conn, creds)
        conn.seller_id    = account.account_id
        conn.seller_name  = account.account_name
        conn.seller_email = account.account_email
        await persist_account_details(conn.id, account, db)
    except Exception as exc:
        logger.warning("Failed to fetch account details for %s: %s", market.slug, exc)

    conn.status       = ConnectionStatus.CONNECTED
    conn.connected_at = datetime.utcnow()
    conn.error_message = None

    await audit_service.record(
        db, AuditAction.OAUTH_CALLBACK,
        company_id    = company_id,
        connection_id = conn.id,
        performed_by  = performed_by,
        new_value     = {"marketplace": market.slug, "seller_id": conn.seller_id},
        ip_address    = ip_address,
    )

    return conn


async def cleanup_expired_states(db: AsyncSession) -> int:
    """Delete OAuth state tokens that have expired. Returns count deleted."""
    result = await db.execute(
        delete(OAuthState).where(OAuthState.expires_at <= datetime.utcnow())
    )
    return result.rowcount
