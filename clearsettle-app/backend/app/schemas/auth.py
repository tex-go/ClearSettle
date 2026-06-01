"""
Pydantic schemas for the auth endpoints.
"""
import re
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

from app.core.security import validate_password_strength


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    # ── Account ────────────────────────────────────────────────────────────────
    email:            EmailStr
    phone:            str
    password:         str
    confirm_password: str
    name:             str

    # ── Role — defaults to company_admin for self-registration ────────────────
    role: str = "company_admin"

    # ── Business profile — mandatory ──────────────────────────────────────────
    company_name: str
    state:        str

    # ── Business profile — optional ───────────────────────────────────────────
    gstin:             Optional[str] = None
    pan:               Optional[str] = None
    city:              Optional[str] = None
    pincode:           Optional[str] = None
    address:           Optional[str] = None
    website:           Optional[str] = None
    industry:          Optional[str] = None
    monthly_gmv_range: Optional[str] = None
    active_platforms:  list[str] = []

    # ── Banking — all optional ────────────────────────────────────────────────
    bank_name:           Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc:           Optional[str] = None
    bank_account_name:   Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self

    @field_validator("gstin")
    @classmethod
    def gstin_format(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid GSTIN format (expected: 22AAAAA0000A1Z5)")
        return v.upper()

    @field_validator("phone")
    @classmethod
    def phone_format(cls, v: str) -> str:
        digits = re.sub(r"[\s\-\(\)\+]", "", v)
        if not digits.isdigit() or len(digits) < 10:
            raise ValueError("Invalid phone number")
        return v

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        allowed = {
            "company_admin", "business_owner", "finance_manager", "accountant",
            "reconciliation_analyst", "gst_consultant", "auditor",
            "ca_admin", "ca_reviewer", "ca_staff", "ca_viewer",
            "branch_manager", "branch_accountant", "branch_viewer",
            "admin", "member", "finance", "seller", "viewer",
        }
        if v not in allowed:
            raise ValueError(f"Invalid role: {v}")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Returned by the /refresh endpoint — new pair of tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Client sends the refresh token to revoke it on logout."""
    refresh_token: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v


class VerifyEmailRequest(BaseModel):
    token: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        allowed = {"admin", "member", "finance", "analyst", "viewer", "support"}
        if v not in allowed:
            raise ValueError(f"Role must be one of: {', '.join(sorted(allowed))}")
        return v


class AcceptInviteRequest(BaseModel):
    token: str
    name: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        errors = validate_password_strength(v)
        if errors:
            raise ValueError("; ".join(errors))
        return v
