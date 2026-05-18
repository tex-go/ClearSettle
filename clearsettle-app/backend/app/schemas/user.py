"""
Pydantic schemas for user-related responses.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CompanyBrief(BaseModel):
    id: UUID
    name: str
    gstin: str | None = None
    city: str | None = None
    industry: str | None = None

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    """Safe user representation — never includes hashed_password."""
    id: UUID
    email: str
    name: str | None
    role: str
    is_active: bool
    companies: list[CompanyBrief] = []
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Flat profile returned by /auth/me for frontend consumption."""
    id: str
    email: str
    name: str | None
    role: str
    company: str | None = None
    gstin: str | None = None
    city: str | None = None
    industry: str | None = None
    permissions: list[str] = []


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    class Config:
        # Prevent accidental logging of password fields
        json_schema_extra = {"example": {"current_password": "***", "new_password": "***"}}


class UpdateProfileRequest(BaseModel):
    name: str | None = None
