"""
Platform connection service.

All business logic for managing marketplace connections lives here.
The router stays thin — it only handles HTTP input/output.

Credential security rules:
  - Credentials are ALWAYS encrypted with Fernet before hitting the DB.
  - Plaintext credentials are NEVER returned to callers.
  - api_key_display stores a masked preview only (first 4 + last 4 chars).
  - credentials_enc stores a Fernet-encrypted JSON blob of the full dict.
"""
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.db.models import PlatformConnection
from app.schemas.platform import (
    CheckResult,
    ConnectionOut,
    ConnectionSummary,
    ConnectionsResponse,
    CredentialFieldOut,
    CredentialsOut,
    TestConnectionResult,
    get_platform_meta,
)

logger = logging.getLogger(__name__)


# ── Credential helpers (sync — no DB) ────────────────────────────────────────

def _mask(value: str) -> str:
    """Return a masked display version of a credential value."""
    if not value:
        return ""
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


def _store_credentials(conn: PlatformConnection, credentials: dict[str, str]) -> None:
    """
    Encrypt and persist a credentials dict into a PlatformConnection.
    Also sets api_key_display if an 'api_key' field is present.

    Does NOT commit — caller is responsible for `await db.commit()`.
    """
    conn.credentials_enc = encrypt(json.dumps(credentials))
    if "api_key" in credentials:
        conn.api_key_display = _mask(credentials["api_key"])


def _load_credentials(conn: PlatformConnection) -> dict[str, str] | None:
    """
    Decrypt and return the credentials dict, or None if nothing stored.
    Raises ValueError if decryption fails (key mismatch).
    """
    if not conn.credentials_enc:
        return None
    raw = decrypt(conn.credentials_enc)
    return json.loads(raw)


def _build_connection_out(conn: PlatformConnection) -> ConnectionOut:
    meta = get_platform_meta(conn.platform)

    # seller_id: prefer generic field, fall back to Amazon's field
    seller_id = conn.platform_seller_id or conn.sp_selling_partner_id

    # marketplace_id: Amazon-specific; extend here when others support it
    marketplace_id = conn.sp_marketplace_id

    credentials_present = bool(
        conn.credentials_enc                # generic platforms
        or conn.sp_refresh_token_enc        # Amazon OAuth
    )

    return ConnectionOut(
        id=conn.platform,
        platform=conn.platform,
        platform_name=meta["name"],
        auth_type=meta["auth_type"],
        color=meta["color"],
        status=conn.status,
        seller_id=seller_id,
        marketplace_id=marketplace_id,
        credentials_present=credentials_present,
        webhook_url=conn.webhook_url,
        last_sync_at=conn.last_sync_at,
        last_sync_error=conn.last_sync_error,
        total_orders_synced=conn.total_orders_synced or 0,
        connection_id=str(conn.id),
        key=conn.api_key_display or "",
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


# ── DB helpers ────────────────────────────────────────────────────────────────

async def _get_conn(platform: str, company_id, db: AsyncSession) -> PlatformConnection | None:
    result = await db.execute(
        select(PlatformConnection).where(
            PlatformConnection.company_id == company_id,
            PlatformConnection.platform   == platform,
        )
    )
    return result.scalar_one_or_none()


async def _get_conn_or_404(platform: str, company_id, db: AsyncSession) -> PlatformConnection:
    from fastapi import HTTPException
    conn = await _get_conn(platform, company_id, db)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not configured for this company")
    return conn


async def _get_or_create(platform: str, company_id, db: AsyncSession) -> PlatformConnection:
    conn = await _get_conn(platform, company_id, db)
    if not conn:
        conn = PlatformConnection(company_id=company_id, platform=platform)
        db.add(conn)
        await db.flush()
    return conn


# ── Public service API ────────────────────────────────────────────────────────

async def list_connections(company_id, db: AsyncSession) -> ConnectionsResponse:
    """Return all platform connections for a company, padded with disconnected stubs."""
    from app.schemas.platform import PLATFORM_REGISTRY

    result = await db.execute(
        select(PlatformConnection)
        .where(PlatformConnection.company_id == company_id)
        .order_by(PlatformConnection.platform)
    )
    db_conns = {c.platform: c for c in result.scalars().all()}

    items: list[ConnectionOut] = []
    for platform in PLATFORM_REGISTRY:
        if platform in db_conns:
            items.append(_build_connection_out(db_conns[platform]))
        else:
            # Return a virtual disconnected entry so the frontend always shows all platforms
            meta = get_platform_meta(platform)
            items.append(ConnectionOut(
                id=platform,
                platform=platform,
                platform_name=meta["name"],
                auth_type=meta["auth_type"],
                color=meta["color"],
                status="disconnected",
                credentials_present=False,
                connection_id="",
                key="",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))

    summary = ConnectionSummary(
        total=len(items),
        connected=sum(1 for i in items if i.status == "connected"),
        disconnected=sum(1 for i in items if i.status == "disconnected"),
        pending=sum(1 for i in items if i.status == "pending"),
        error=sum(1 for i in items if i.status == "error"),
        oauth_pending=sum(1 for i in items if i.status == "oauth_pending"),
    )
    return ConnectionsResponse(items=items, summary=summary)


async def get_connection(platform: str, company_id, db: AsyncSession) -> ConnectionOut:
    conn = await _get_conn_or_404(platform, company_id, db)
    return _build_connection_out(conn)


async def connect_api_key(
    platform: str,
    credentials: dict[str, str],
    company_id,
    db: AsyncSession,
    *,
    seller_id: Optional[str] = None,
    webhook_url: Optional[str] = None,
) -> ConnectionOut:
    """
    Store encrypted credentials for an API-key platform and mark it connected.

    Validates that all required fields for the platform are present.
    Raises 400 on missing required fields.
    Raises 422 if the platform uses OAuth (use /sp-api/authorize instead).
    """
    from fastapi import HTTPException
    from app.schemas.platform import PLATFORM_REGISTRY

    meta = get_platform_meta(platform)
    if meta.get("sp_api"):
        raise HTTPException(
            status_code=422,
            detail=f"{platform} uses OAuth2. Use the SP API authorize endpoint instead.",
        )

    required = meta.get("required_cred_fields", [])
    missing = [f for f in required if f not in credentials or not credentials[f].strip()]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required credential fields for {platform}: {', '.join(missing)}",
        )

    conn = await _get_or_create(platform, company_id, db)
    _store_credentials(conn, credentials)

    if seller_id:
        conn.platform_seller_id = seller_id
    elif "seller_id" in credentials:
        conn.platform_seller_id = credentials["seller_id"]

    if webhook_url:
        conn.webhook_url = webhook_url

    conn.status     = "connected"
    conn.updated_at = datetime.utcnow()
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    logger.info("Platform connected: %s (company=%s)", platform, company_id)
    return _build_connection_out(conn)


async def update_credentials(
    platform: str,
    credentials: dict[str, str],
    company_id,
    db: AsyncSession,
    *,
    seller_id: Optional[str] = None,
    webhook_url: Optional[str] = None,
) -> ConnectionOut:
    """Update stored credentials without changing connection status."""
    conn = await _get_conn_or_404(platform, company_id, db)
    _store_credentials(conn, credentials)

    if seller_id is not None:
        conn.platform_seller_id = seller_id
    if webhook_url is not None:
        conn.webhook_url = webhook_url

    conn.updated_at = datetime.utcnow()
    db.add(conn)
    await db.commit()
    await db.refresh(conn)
    return _build_connection_out(conn)


async def disconnect(platform: str, company_id, db: AsyncSession) -> ConnectionOut:
    """Revoke stored credentials and set status to disconnected."""
    conn = await _get_conn_or_404(platform, company_id, db)

    # Wipe all credentials
    conn.credentials_enc           = None
    conn.api_key_display           = None
    conn.webhook_secret_enc        = None
    conn.platform_seller_id        = None

    # Wipe Amazon tokens
    conn.sp_refresh_token_enc      = None
    conn.sp_access_token_enc       = None
    conn.sp_access_token_expires_at = None
    conn.sp_client_secret_enc      = None
    conn.sp_selling_partner_id     = None
    conn.oauth_state               = None

    conn.status     = "disconnected"
    conn.updated_at = datetime.utcnow()
    db.add(conn)
    await db.commit()
    await db.refresh(conn)

    logger.info("Platform disconnected: %s (company=%s)", platform, company_id)
    return _build_connection_out(conn)


async def get_masked_credentials(platform: str, company_id, db: AsyncSession) -> CredentialsOut:
    """
    Return masked (never plaintext) credential info.
    Used by GET /{pid}/credentials to show what's stored without exposing values.
    """
    conn = await _get_conn_or_404(platform, company_id, db)
    meta = get_platform_meta(platform)

    fields: list[CredentialFieldOut] = []

    if meta.get("sp_api"):
        # Amazon: show which tokens are present
        fields = [
            CredentialFieldOut(key="client_id",     masked_value=_mask(conn.sp_client_id or ""), present=bool(conn.sp_client_id)),
            CredentialFieldOut(key="refresh_token",  masked_value="[encrypted]" if conn.sp_refresh_token_enc else "", present=bool(conn.sp_refresh_token_enc)),
            CredentialFieldOut(key="access_token",   masked_value="[encrypted]" if conn.sp_access_token_enc else "", present=bool(conn.sp_access_token_enc)),
        ]
        if conn.sp_access_token_expires_at:
            fields.append(CredentialFieldOut(
                key="token_expires_at",
                masked_value=conn.sp_access_token_expires_at.isoformat(),
                present=True,
            ))
    else:
        creds = _load_credentials(conn) or {}
        for field_name in meta.get("required_cred_fields", []) + meta.get("optional_cred_fields", []):
            value = creds.get(field_name, "")
            fields.append(CredentialFieldOut(
                key=field_name,
                masked_value=_mask(value) if value else "",
                present=bool(value),
            ))

    return CredentialsOut(
        platform=platform,
        auth_type=meta["auth_type"],
        fields=fields,
        seller_id=conn.platform_seller_id or conn.sp_selling_partner_id,
        webhook_url=conn.webhook_url,
    )


async def test_connection(platform: str, company_id, db: AsyncSession) -> TestConnectionResult:
    """
    Validate a connection's configuration without making live API calls.

    Checks performed:
      1. Connection row exists
      2. Status is 'connected'
      3. Credentials are stored
      4. Credentials decrypt successfully
      5. All required fields are present and non-empty
      6. (Amazon) tokens stored + expiry tracked

    NOTE: Live API call testing (e.g. hitting /sellers endpoint) is reserved
    for a future session when sync logic is implemented.
    """
    conn = await _get_conn(platform, company_id, db)
    meta = get_platform_meta(platform)
    checks: list[CheckResult] = []
    all_passed = True

    # ── Check 1: Row exists ───────────────────────────────────────────────────
    if not conn:
        return TestConnectionResult(
            platform=platform,
            status="unconfigured",
            message=f"{meta['name']} has not been configured yet.",
            checks=[CheckResult(name="connection_exists", passed=False, detail="No connection record found")],
        )
    checks.append(CheckResult(name="connection_exists", passed=True, detail="Connection record found"))

    # ── Check 2: Status ───────────────────────────────────────────────────────
    status_ok = conn.status == "connected"
    checks.append(CheckResult(
        name="status",
        passed=status_ok,
        detail=f"Status is '{conn.status}'" + ("" if status_ok else " — expected 'connected'"),
    ))
    if not status_ok:
        all_passed = False

    if meta.get("sp_api"):
        # ── Amazon-specific checks ────────────────────────────────────────────
        has_refresh = bool(conn.sp_refresh_token_enc)
        checks.append(CheckResult(
            name="refresh_token_stored",
            passed=has_refresh,
            detail="Refresh token encrypted and stored" if has_refresh else "No refresh token — OAuth not completed",
        ))
        if not has_refresh:
            all_passed = False

        has_access = bool(conn.sp_access_token_enc)
        checks.append(CheckResult(
            name="access_token_stored",
            passed=has_access,
            detail="Access token encrypted and stored" if has_access else "No access token — refresh required",
        ))

        if conn.sp_access_token_expires_at:
            is_valid = conn.sp_access_token_expires_at > datetime.utcnow()
            checks.append(CheckResult(
                name="access_token_valid",
                passed=is_valid,
                detail=f"Expires at {conn.sp_access_token_expires_at.isoformat()}" + ("" if is_valid else " (EXPIRED — will auto-refresh on next sync)"),
            ))

        has_seller = bool(conn.sp_selling_partner_id)
        checks.append(CheckResult(
            name="seller_id_present",
            passed=has_seller,
            detail=f"Selling Partner ID: {conn.sp_selling_partner_id}" if has_seller else "No Selling Partner ID",
        ))
        if not has_seller:
            all_passed = False

    else:
        # ── API-key platform checks ───────────────────────────────────────────
        has_creds = bool(conn.credentials_enc)
        checks.append(CheckResult(
            name="credentials_stored",
            passed=has_creds,
            detail="Encrypted credentials present" if has_creds else "No credentials stored",
        ))
        if not has_creds:
            all_passed = False
        else:
            # Try to decrypt
            try:
                creds = _load_credentials(conn)
                checks.append(CheckResult(name="credentials_decrypt", passed=True, detail="Decryption successful"))

                # Validate required fields
                required = meta.get("required_cred_fields", [])
                missing = [f for f in required if not creds.get(f, "").strip()]
                fields_ok = len(missing) == 0
                checks.append(CheckResult(
                    name="required_fields",
                    passed=fields_ok,
                    detail=(
                        f"All required fields present: {', '.join(required)}"
                        if fields_ok
                        else f"Missing required fields: {', '.join(missing)}"
                    ),
                ))
                if not fields_ok:
                    all_passed = False

            except Exception as exc:
                checks.append(CheckResult(name="credentials_decrypt", passed=False, detail=f"Decryption failed: {exc}"))
                all_passed = False

        # Seller ID check
        if conn.platform_seller_id:
            checks.append(CheckResult(name="seller_id_present", passed=True, detail=f"Seller ID: {conn.platform_seller_id}"))

    overall_status = "ok" if all_passed else ("warning" if conn.status == "connected" else "failed")
    message = (
        f"{meta['name']} is connected and configured correctly."
        if all_passed
        else f"{meta['name']} has configuration issues — review the checks below."
    )

    return TestConnectionResult(
        platform=platform,
        status=overall_status,
        message=message,
        checks=checks,
    )
