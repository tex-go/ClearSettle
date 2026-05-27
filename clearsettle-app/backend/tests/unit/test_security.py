"""Unit tests for app.core.security — no DB, no HTTP."""
import time
from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    generate_secure_token,
    hash_password,
    hash_refresh_token,
    hash_secure_token,
    validate_password_strength,
    verify_password,
)


# ── password hashing ──────────────────────────────────────────────────────────

class TestHashPassword:
    def test_returns_bcrypt_hash(self):
        h = hash_password("MySecret@1")
        assert h.startswith("$2b$")

    def test_different_hashes_same_password(self):
        h1 = hash_password("MySecret@1")
        h2 = hash_password("MySecret@1")
        assert h1 != h2  # salt randomises each hash

    def test_verify_correct(self):
        h = hash_password("MySecret@1")
        assert verify_password("MySecret@1", h) is True

    def test_verify_wrong(self):
        h = hash_password("MySecret@1")
        assert verify_password("wrong", h) is False

    def test_verify_empty_plain(self):
        h = hash_password("MySecret@1")
        assert verify_password("", h) is False

    def test_verify_malformed_hash(self):
        assert verify_password("MySecret@1", "not-a-hash") is False


# ── password strength validation ──────────────────────────────────────────────

class TestValidatePasswordStrength:
    def test_valid_password_returns_empty(self):
        assert validate_password_strength("TestPass@1234!") == []

    def test_too_short(self):
        errs = validate_password_strength("Abc@1")
        assert any("10" in e for e in errs)

    def test_no_uppercase(self):
        errs = validate_password_strength("testpass@1234!")
        assert any("uppercase" in e.lower() for e in errs)

    def test_no_lowercase(self):
        errs = validate_password_strength("TESTPASS@1234!")
        assert any("lowercase" in e.lower() for e in errs)

    def test_no_digit(self):
        errs = validate_password_strength("TestPass@ABC!")
        assert any("digit" in e.lower() for e in errs)

    def test_no_special(self):
        errs = validate_password_strength("TestPass12345")
        assert any("special" in e.lower() for e in errs)

    def test_multiple_failures(self):
        errs = validate_password_strength("abc")
        assert len(errs) >= 3  # short + no upper + no digit + no special

    def test_boundary_exactly_10(self):
        assert validate_password_strength("Abcde@1234") == []

    def test_boundary_9_chars(self):
        errs = validate_password_strength("Abcde@123")
        assert any("10" in e for e in errs)


# ── JWT access token ──────────────────────────────────────────────────────────

class TestAccessToken:
    def test_create_and_decode_roundtrip(self):
        token = create_access_token("user@example.com")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "user@example.com"
        assert payload["type"] == "access"

    def test_has_jti(self):
        token = create_access_token("user@example.com")
        payload = decode_access_token(token)
        assert "jti" in payload
        assert len(payload["jti"]) > 0

    def test_extra_claims_included(self):
        token = create_access_token("u@e.com", extra_claims={"role": "admin", "id": "uuid-123"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"
        assert payload["id"] == "uuid-123"

    def test_expired_token_returns_none(self):
        token = create_access_token("u@e.com", expires_delta=timedelta(seconds=-1))
        assert decode_access_token(token) is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("u@e.com")
        tampered = token[:-4] + "XXXX"
        assert decode_access_token(tampered) is None

    def test_garbage_string_returns_none(self):
        assert decode_access_token("not.a.jwt") is None

    def test_empty_string_returns_none(self):
        assert decode_access_token("") is None

    def test_jti_unique_per_token(self):
        t1 = create_access_token("u@e.com")
        t2 = create_access_token("u@e.com")
        p1 = decode_access_token(t1)
        p2 = decode_access_token(t2)
        assert p1["jti"] != p2["jti"]


# ── Refresh token ─────────────────────────────────────────────────────────────

class TestRefreshToken:
    def test_generate_is_string(self):
        tok = generate_refresh_token()
        assert isinstance(tok, str)
        assert len(tok) > 40  # URL-safe base64 of 64 bytes

    def test_generate_unique(self):
        assert generate_refresh_token() != generate_refresh_token()

    def test_hash_is_hex(self):
        tok = generate_refresh_token()
        h = hash_refresh_token(tok)
        assert len(h) == 64  # SHA-256 hex = 64 chars
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_token_same_hash(self):
        tok = generate_refresh_token()
        assert hash_refresh_token(tok) == hash_refresh_token(tok)

    def test_different_tokens_different_hash(self):
        t1 = generate_refresh_token()
        t2 = generate_refresh_token()
        assert hash_refresh_token(t1) != hash_refresh_token(t2)


# ── One-time secure tokens ────────────────────────────────────────────────────

class TestSecureToken:
    def test_generate_secure_token_is_string(self):
        tok = generate_secure_token()
        assert isinstance(tok, str)

    def test_default_length_adequate(self):
        tok = generate_secure_token()
        assert len(tok) >= 32

    def test_custom_nbytes(self):
        tok = generate_secure_token(nbytes=16)
        assert len(tok) >= 16

    def test_unique(self):
        assert generate_secure_token() != generate_secure_token()

    def test_hash_secure_token_is_hex(self):
        tok = generate_secure_token()
        h = hash_secure_token(tok)
        assert len(h) == 64

    def test_hash_deterministic(self):
        tok = generate_secure_token()
        assert hash_secure_token(tok) == hash_secure_token(tok)
