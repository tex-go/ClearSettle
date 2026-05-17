"""
Authentication service — all DB-backed auth logic lives here.

Keeps routers thin: routers validate HTTP input/output, this service
handles the business rules.
"""
import logging
from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.core.config import get_settings
from app.db.models import Company, RefreshToken, User

logger = logging.getLogger(__name__)

_EXPIRES_IN = get_settings().access_token_expire_minutes * 60


# ── Internal helpers ──────────────────────────────────────────────────────────

async def get_user_by_email(email: str, db: AsyncSession) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.companies))
        .where(User.email == email, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


async def get_user_by_id(user_id, db: AsyncSession) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.companies))
        .where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()


def _build_token_pair(user: User) -> tuple[str, str]:
    """Return (access_token, refresh_token_plaintext)."""
    access = create_access_token(
        user.email,
        extra_claims={"id": str(user.id), "role": user.role},
    )
    refresh = generate_refresh_token()
    return access, refresh


def _user_profile(user: User) -> dict:
    company = user.companies[0] if user.companies else None
    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "company": company.name if company else None,
        "gstin": company.gstin if company else None,
        "city": company.city if company else None,
        "industry": company.industry if company else None,
    }


async def _persist_refresh_token(
    user_id,
    token_plain: str,
    db: AsyncSession,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> None:
    rt = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(token_plain),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(rt)
    await db.commit()


# ── Public service methods ────────────────────────────────────────────────────

async def login(
    email: str,
    password: str,
    db: AsyncSession,
    *,
    request: Request | None = None,
) -> dict:
    """
    Verify credentials and return token pair + user profile.
    Raises 401 on bad credentials.
    """
    user = await get_user_by_email(email, db)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access, refresh = _build_token_pair(user)

    ua = request.headers.get("user-agent") if request else None
    ip = None
    if request:
        fwd = request.headers.get("X-Forwarded-For")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)

    await _persist_refresh_token(user.id, refresh, db, user_agent=ua, ip_address=ip)

    logger.info("Login successful: user=%s", email)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": _EXPIRES_IN,
        "user": _user_profile(user),
    }


async def register(
    email: str,
    password: str,
    name: str,
    company_name: str,
    db: AsyncSession,
    *,
    request: Request | None = None,
) -> dict:
    """
    Create user + company, return token pair.
    Raises 409 if email is already registered.
    """
    existing = await get_user_by_email(email, db)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name,
        role="admin",
        is_active=True,
    )
    db.add(user)
    await db.flush()  # populate user.id before creating Company

    company = Company(user_id=user.id, name=company_name)
    db.add(company)
    await db.commit()
    await db.refresh(user)

    # Re-load with relationships
    user = await get_user_by_id(user.id, db)

    access, refresh = _build_token_pair(user)

    ua = request.headers.get("user-agent") if request else None
    ip = None
    if request:
        fwd = request.headers.get("X-Forwarded-For")
        ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)

    await _persist_refresh_token(user.id, refresh, db, user_agent=ua, ip_address=ip)

    logger.info("Registered new user: %s (company: %s)", email, company_name)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": _EXPIRES_IN,
        "user": _user_profile(user),
    }


async def refresh_tokens(token_plain: str, db: AsyncSession) -> dict:
    """
    Token rotation: validate the incoming refresh token, revoke it,
    issue a new access + refresh token pair.
    Raises 401 if the token is invalid, expired, or already revoked.
    """
    token_hash = hash_refresh_token(token_plain)
    now = datetime.utcnow()

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked.is_(False),
            RefreshToken.expires_at > now,
        )
    )
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    # Revoke the old token (rotation)
    rt.revoked = True
    db.add(rt)

    user = await get_user_by_id(rt.user_id, db)
    if not user or not user.is_active:
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    access, new_refresh = _build_token_pair(user)

    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_refresh),
        expires_at=refresh_token_expiry(),
        user_agent=rt.user_agent,
        ip_address=rt.ip_address,
    )
    db.add(new_rt)
    await db.commit()

    return {
        "access_token": access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "expires_in": _EXPIRES_IN,
    }


async def logout(token_plain: str | None, db: AsyncSession) -> None:
    """Revoke the given refresh token (best-effort; no error if not found)."""
    if not token_plain:
        return
    token_hash = hash_refresh_token(token_plain)
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    rt = result.scalar_one_or_none()
    if rt:
        rt.revoked = True
        db.add(rt)
        await db.commit()


async def change_password(
    user: User,
    current_password: str,
    new_password: str,
    db: AsyncSession,
) -> None:
    """
    Change password and revoke all existing refresh tokens (force re-login).
    Raises 400 on wrong current password.
    """
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    db.add(user)

    # Revoke all refresh tokens for security
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked.is_(False),
        )
    )
    for rt in result.scalars().all():
        rt.revoked = True
        db.add(rt)

    await db.commit()
    logger.info("Password changed for user %s; all refresh tokens revoked", user.email)
