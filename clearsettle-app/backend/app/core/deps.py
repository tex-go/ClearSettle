"""
FastAPI dependency injection: DB session + current-user resolution.
"""
from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.auth import decode_token
from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


# ── Database session ──────────────────────────────────────────────────────────

def get_db() -> Generator:
    """
    Yields a SQLAlchemy session and guarantees it is closed after the request.
    Only available when DATABASE_URL is configured.
    """
    settings = get_settings()
    if not settings.database_url:
        raise HTTPException(
            status_code=503,
            detail="Database not configured. Set DATABASE_URL environment variable.",
        )
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_optional() -> Generator:
    """
    Yields a session when DB is available, otherwise yields None.
    Used in routes that fall back to mock data when no DB is configured.
    """
    settings = get_settings()
    if not settings.database_url:
        yield None
        return
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session | None = Depends(get_db_optional),
):
    """
    Resolves the current user from a Bearer JWT.
    - With DB: looks up User row and returns ORM object.
    - Without DB: returns the in-memory DEMO_USER dict.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    email: str = payload.get("sub")
    if not email:
        raise credentials_exception

    if db is not None:
        from app.db.models import User
        user = db.query(User).filter(User.email == email, User.is_active == True).first()
        if not user:
            raise credentials_exception
        return user

    # No DB — validate against demo user
    from app.core.auth import DEMO_USER
    if email != DEMO_USER["email"]:
        raise credentials_exception
    return DEMO_USER


def require_db_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
):
    """Like get_current_user but always requires a DB-backed user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    email: str = payload.get("sub")
    if not email:
        raise credentials_exception

    from app.db.models import User
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user:
        raise credentials_exception
    return user
