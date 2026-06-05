"""
app/core/security.py — Single source of truth for tokens and password hashing.

Security principles:
  - bcrypt rounds=12 for password hashing (≈300ms on modern hardware — intentionally slow)
  - Access tokens expire in 30 minutes (configurable)
  - Refresh tokens are opaque (URL-safe random bytes), stored as SHA-256 hash
  - JTI (JWT ID) claim on every access token for future blacklisting support
  - One-time secure tokens (password reset / email verification) use SHA-256 hash storage
  - Password strength validation enforced at creation time
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


# ── Password hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """bcrypt hash with rounds=12. ~300ms intentional delay deters brute force."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time bcrypt comparison. Returns False on any error."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def validate_password_strength(password: str) -> list[str]:
    """
    Return a list of unmet requirement messages.
    Empty list = password passes all checks.

    Why these rules: NIST SP 800-63B + fintech standard practice.
    Length is the most important factor; complexity adds secondary entropy.
    """
    errors: list[str] = []
    if len(password) < 10:
        errors.append("At least 10 characters required")
    if not any(c.isupper() for c in password):
        errors.append("At least one uppercase letter required")
    if not any(c.islower() for c in password):
        errors.append("At least one lowercase letter required")
    if not any(c.isdigit() for c in password):
        errors.append("At least one digit required")
    if not any(c in r"!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("At least one special character required (!@#$%^&*…)")
    return errors


# ── JWT access token ──────────────────────────────────────────────────────────

def create_access_token(
    subject: Any,
    *,
    extra_claims: dict | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed HS256 JWT access token.

    Claims included:
      sub  - user email (the identity principal)
      jti  - unique token ID (UUID4) for future blacklist / revocation support
      iat  - issued-at timestamp
      exp  - expiry (default: 30 minutes from settings)
      type - "access" — prevents refresh tokens being accepted as access tokens
      id   - user UUID (via extra_claims)
      role - user role (via extra_claims)
      org  - primary company/org ID (via extra_claims)
    """
    settings = get_settings()
    now = datetime.utcnow()
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )

    payload: dict = {
        "sub":  str(subject),
        "jti":  str(uuid.uuid4()),   # Unique per-token ID
        "iat":  now,
        "exp":  expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict | None:
    """
    Validate and decode a JWT access token.
    Returns the payload dict or None if invalid, expired, or wrong type.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        # Reject tokens issued as refresh tokens or any other type
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


# ── Refresh token ─────────────────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    Cryptographically secure 64-byte opaque token (URL-safe base64).
    This plaintext value is sent to the client ONCE and never stored.
    Only the SHA-256 hash is persisted in the database.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest — stored in DB. Plaintext never persisted."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    settings = get_settings()
    return datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)


# ── One-time secure tokens ────────────────────────────────────────────────────
# Used for: password reset, email verification, team invitations.
# Pattern: generate plaintext → send to user → store SHA-256 hash in DB.
# On redemption: hash the submitted value → compare to DB → mark used.

def generate_secure_token(nbytes: int = 32) -> str:
    """URL-safe random token. Default 32 bytes = 256 bits of entropy."""
    return secrets.token_urlsafe(nbytes)


def hash_secure_token(token: str) -> str:
    """SHA-256 hex digest for secure token storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Convenience wrapper used by social_auth/provider_service.py
def create_refresh_token() -> tuple[str, str]:
    """Return (raw_token, hashed_token). Raw is sent to client; hash is stored in DB."""
    raw = generate_refresh_token()
    return raw, hash_refresh_token(raw)


# Backward-compat alias (used by auth_service.py)
REFRESH_TOKEN_EXPIRE_DAYS: int = 7
