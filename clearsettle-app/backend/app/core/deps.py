"""
FastAPI dependency injection: async DB session + current-user resolution.

All dependencies are async to match the AsyncSession / asyncpg setup.
"""
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_access_token
from app.db.database import AsyncSessionLocal

bearer = HTTPBearer(auto_error=False)


# ── Database sessions ─────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async session.  Raises 503 when DATABASE_URL is not configured.
    Use this for endpoints that *require* a live database.
    """
    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured — set DATABASE_URL.",
        )
    async with AsyncSessionLocal() as session:
        yield session


async def get_db_optional() -> AsyncGenerator[AsyncSession | None, None]:
    """
    Yield a session when available, otherwise yield *None*.
    Routes that fall back to mock data use this dependency.
    """
    if AsyncSessionLocal is None:
        yield None
        return
    async with AsyncSessionLocal() as session:
        yield session


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession | None = Depends(get_db_optional),
):
    """
    Resolve the current user from a Bearer JWT.

    With DB:    queries the users table, returns an ORM User object.
    Without DB: validates against the in-memory DEMO_USER (mock-data mode).
    """
    if not credentials:
        raise _credentials_exception()

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise _credentials_exception()

    email: str | None = payload.get("sub")
    if not email:
        raise _credentials_exception()

    if db is not None:
        from app.db.models import User
        result = await db.execute(
            select(User)
            .options(selectinload(User.companies))
            .where(
                User.email == email,
                User.is_active.is_(True),
                User.deleted_at.is_(None),
            )
        )
        user = result.scalar_one_or_none()
        if not user:
            raise _credentials_exception()
        return user

    # ── mock-data mode ────────────────────────────────────────────────────────
    from app.core.auth import DEMO_USER
    if email != DEMO_USER["email"]:
        raise _credentials_exception()
    return DEMO_USER


async def require_db_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Like get_current_user but always requires a DB-backed User.
    Use for endpoints that must write to the database.
    """
    if not credentials:
        raise _credentials_exception()

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise _credentials_exception()

    email: str | None = payload.get("sub")
    if not email:
        raise _credentials_exception()

    from app.db.models import User
    result = await db.execute(
        select(User)
        .options(selectinload(User.companies))
        .where(
            User.email == email,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise _credentials_exception()
    return user


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
