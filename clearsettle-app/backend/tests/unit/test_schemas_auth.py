"""Unit tests for app.schemas.auth Pydantic models."""
import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    AcceptInviteRequest,
    ForgotPasswordRequest,
    InviteRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
)

VALID_PW = "TestPass@1234!"
VALID_GSTIN = "33ABCDE1234F1Z5"


def base_register(**overrides) -> dict:
    d = {
        "email":            "user@example.com",
        "phone":            "+91-9876543210",
        "password":         VALID_PW,
        "confirm_password": VALID_PW,
        "name":             "Test User",
        "company_name":     "Test Corp",
        "gstin":            VALID_GSTIN,
        "state":            "Tamil Nadu",
        "active_platforms": ["Amazon"],
    }
    d.update(overrides)
    return d


# ── LoginRequest ──────────────────────────────────────────────────────────────

class TestLoginRequest:
    def test_valid(self):
        r = LoginRequest(email="a@b.com", password="secret")
        assert r.email == "a@b.com"

    def test_missing_email_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(password="secret")

    def test_missing_password_raises(self):
        with pytest.raises(ValidationError):
            LoginRequest(email="a@b.com")


# ── RegisterRequest ───────────────────────────────────────────────────────────

class TestRegisterRequest:
    def test_valid_payload(self):
        r = RegisterRequest(**base_register())
        assert r.email == "user@example.com"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError) as exc:
            RegisterRequest(**base_register(password="weak", confirm_password="weak"))
        assert "10" in str(exc.value) or "uppercase" in str(exc.value).lower()

    def test_passwords_mismatch_rejected(self):
        with pytest.raises(ValidationError) as exc:
            RegisterRequest(**base_register(confirm_password="DifferentPass@1!"))
        assert "match" in str(exc.value).lower()

    def test_invalid_gstin_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**base_register(gstin="INVALID"))

    def test_gstin_uppercased(self):
        r = RegisterRequest(**base_register(gstin=VALID_GSTIN.lower()))
        assert r.gstin == VALID_GSTIN

    def test_invalid_phone_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**base_register(phone="123"))

    def test_empty_platforms_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**base_register(active_platforms=[]))

    def test_multiple_platforms_allowed(self):
        r = RegisterRequest(**base_register(active_platforms=["Amazon", "Flipkart"]))
        assert len(r.active_platforms) == 2

    def test_optional_fields_default_none(self):
        r = RegisterRequest(**base_register())
        assert r.pan is None
        assert r.city is None

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(**base_register(email="not-an-email"))

    def test_password_with_all_requirements(self):
        r = RegisterRequest(**base_register(
            password="V3ry$trongPwd!", confirm_password="V3ry$trongPwd!",
        ))
        assert r.password == "V3ry$trongPwd!"


# ── ResetPasswordRequest ──────────────────────────────────────────────────────

class TestResetPasswordRequest:
    def test_valid(self):
        r = ResetPasswordRequest(token="abc123", new_password=VALID_PW)
        assert r.token == "abc123"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            ResetPasswordRequest(token="tok", new_password="weak")


# ── InviteRequest ─────────────────────────────────────────────────────────────

class TestInviteRequest:
    def test_valid_roles(self):
        for role in ("admin", "member", "finance", "analyst", "viewer", "support"):
            r = InviteRequest(email="a@b.com", role=role)
            assert r.role == role

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            InviteRequest(email="a@b.com", role="superuser")

    def test_default_role_member(self):
        r = InviteRequest(email="a@b.com")
        assert r.role == "member"


# ── AcceptInviteRequest ───────────────────────────────────────────────────────

class TestAcceptInviteRequest:
    def test_valid(self):
        r = AcceptInviteRequest(token="tok", name="Alice", password=VALID_PW)
        assert r.name == "Alice"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError):
            AcceptInviteRequest(token="tok", name="Alice", password="weak")


# ── ForgotPasswordRequest ─────────────────────────────────────────────────────

class TestForgotPasswordRequest:
    def test_valid_email(self):
        r = ForgotPasswordRequest(email="a@b.com")
        assert r.email == "a@b.com"

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            ForgotPasswordRequest(email="not-email")


# ── LogoutRequest / RefreshRequest ────────────────────────────────────────────

class TestMiscSchemas:
    def test_logout_optional_token(self):
        r = LogoutRequest()
        assert r.refresh_token is None

    def test_logout_with_token(self):
        r = LogoutRequest(refresh_token="tok")
        assert r.refresh_token == "tok"

    def test_refresh_request_valid(self):
        r = RefreshRequest(refresh_token="sometoken")
        assert r.refresh_token == "sometoken"
