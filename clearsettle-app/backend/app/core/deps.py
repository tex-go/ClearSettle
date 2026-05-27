"""
FastAPI dependency injection: async DB session + current-user resolution.

All dependencies are async to match the AsyncSession / asyncpg setup.
Mock-data mode has been removed — a live DATABASE_URL is always required.
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
    """
    if AsyncSessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured — set DATABASE_URL.",
        )
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
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve the current user from a Bearer JWT against the database.
    Always requires a live DB — mock-data mode has been removed.
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


# Alias kept for router compatibility — mock-data mode has been removed.
# All callers now always get a real DB session.
get_db_optional = get_db


async def require_db_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
):
    """
    Alias for get_current_user — always DB-backed.
    Kept for backwards compatibility with routers already using this name.
    """
    return await get_current_user(credentials=credentials, db=db)


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
