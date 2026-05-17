"""
Pydantic schemas for company-related responses and mutations.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CompanyOut(BaseModel):
    id: UUID
    name: str
    gstin: str | None = None
    city: str | None = None
    industry: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    name: str
    gstin: str | None = None
    city: str | None = None
    industry: str | None = None


class CompanyUpdate(BaseModel):
    name: str | None = None
    gstin: str | None = None
    city: str | None = None
    industry: str | None = None
