"""
Core security utilities: password hashing and JWT management.

This module is the single source of truth for token creation/verification.
It does NOT touch the database — that belongs in auth_service.py.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

# ── Password ──────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Return bcrypt hash of *password* suitable for DB storage."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time password verification."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── Access token ──────────────────────────────────────────────────────────────

def create_access_token(
    subject: Any,
    *,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      Usually user email or user id (serialised to str).
        extra_claims: Additional payload fields (e.g. {"id": "...", "role": "admin"}).
        expires_delta: Override the default expiry from settings.
    """
    settings = get_settings()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    payload: dict = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """
    Decode and verify a JWT access token.
    Returns the payload dict or *None* if invalid/expired.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# ── Refresh token ─────────────────────────────────────────────────────────────

REFRESH_TOKEN_EXPIRE_DAYS = 30


def generate_refresh_token() -> str:
    """Generate a cryptographically secure opaque refresh token (plaintext)."""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest of *token*. This is what we store in the DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
