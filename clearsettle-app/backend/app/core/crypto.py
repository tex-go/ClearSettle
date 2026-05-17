"""
Fernet symmetric encryption for storing SP API credentials at rest.
Key must be a 32-byte URL-safe base64 string (ENCRYPTION_KEY env var).
"""
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet
    key = get_settings().encryption_key
    if not key:
        # Auto-generate an in-process key (data won't survive restarts — fine for dev)
        key = Fernet.generate_key().decode()
        logger.warning(
            "ENCRYPTION_KEY not set — using ephemeral key. "
            "Set ENCRYPTION_KEY in production so credentials survive restarts."
        )
    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(plaintext: str) -> str:
    """Encrypt a string. Returns URL-safe base64 ciphertext."""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    """Decrypt a previously encrypted string. Returns plaintext."""
    if not ciphertext:
        return ""
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt credential — token invalid or key mismatch")
        raise ValueError("Credential decryption failed")


def generate_key() -> str:
    """Utility: generate a new Fernet key (use once, store in ENCRYPTION_KEY)."""
    return Fernet.generate_key().decode()
