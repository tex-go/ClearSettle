"""
Pydantic schemas for the Seller Discovery Engine.

Three resource families:
  SellerLead         — discovered seller profiles
  DiscoveryJob       — crawl run lifecycle
  DiscoveryKeyword   — seed hashtags / competitor accounts
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Shared pagination ─────────────────────────────────────────────────────────

class PageParams(BaseModel):
    page:      int = Field(default=1,  ge=1,   description="1-based page number")
    page_size: int = Field(default=20, ge=1, le=200, description="Rows per page")


class PagedResponse(BaseModel):
    items:     list        # typed by subclasses at router level
    total:     int
    page:      int
    page_size: int
    pages:     int


# ─────────────────────────────────────────────────────────────────────────────
# SELLER LEAD
# ─────────────────────────────────────────────────────────────────────────────

VALID_SOURCES = {"instagram", "linkedin", "google_maps", "shopify", "amazon", "manual"}
VALID_STATUSES = {
    "new",
    "review_pending",   # flagged for human review
    "reviewing",        # reviewer opened it (legacy compat)
    "approved",         # reviewer approved
    "qualified",        # sales-qualified
    "rejected",         # reviewer rejected
    "contact_ready",    # outreach packet prepared
    "contacted",        # outreach sent
    "deleted",          # soft-deleted
}
VALID_OUTREACH_STATUSES = {"pending", "ready", "contacted", "skipped"}
VALID_REVIEW_ACTIONS    = {"approve", "reject", "qualify", "contact_ready", "review", "contacted"}


class SellerLeadCreate(BaseModel):
    username:         str = Field(..., min_length=1, max_length=100)
    source:           str = Field(..., description="instagram | linkedin | …")
    profile_url:      Optional[str] = None
    full_name:        Optional[str] = Field(default=None, max_length=255)
    bio:              Optional[str] = None
    website:          Optional[str] = Field(default=None, max_length=500)
    category:         Optional[str] = Field(default=None, max_length=100)
    profile_image_url:Optional[str] = None
    followers_count:  Optional[int] = Field(default=None, ge=0)
    following_count:  Optional[int] = Field(default=None, ge=0)
    engagement_rate:  Optional[float] = Field(default=None, ge=0, le=1)
    email:            Optional[str] = Field(default=None, max_length=255)
    whatsapp:         Optional[str] = Field(default=None, max_length=20)
    country:          Optional[str] = Field(default=None, max_length=50)
    language:         Optional[str] = Field(default=None, max_length=20)
    discovery_source: Optional[str] = Field(default=None, max_length=50)
    discovery_keyword:Optional[str] = Field(default=None, max_length=200)

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in VALID_SOURCES:
            raise ValueError(f"source must be one of {sorted(VALID_SOURCES)}")
        return v


class SellerLeadPatch(BaseModel):
    full_name:             Optional[str]      = Field(default=None, max_length=255)
    bio:                   Optional[str]      = None
    website:               Optional[str]      = Field(default=None, max_length=500)
    category:              Optional[str]      = Field(default=None, max_length=100)
    profile_image_url:     Optional[str]      = None
    email:                 Optional[str]      = Field(default=None, max_length=255)
    whatsapp:              Optional[str]      = Field(default=None, max_length=20)
    country:               Optional[str]      = Field(default=None, max_length=50)
    language:              Optional[str]      = Field(default=None, max_length=20)
    lead_status:           Optional[str]      = None
    notes:                 Optional[str]      = None
    tags_json:             Optional[str]      = None
    follow_up_at:          Optional[datetime] = None
    assigned_to:           Optional[str]      = Field(default=None, max_length=100)
    # AI fields — updated by the classifier service
    ai_is_ecommerce:       Optional[bool]  = None
    ai_relevance_score:    Optional[float] = Field(default=None, ge=0, le=1)
    ai_confidence_score:   Optional[float] = Field(default=None, ge=0, le=1)
    ai_category:           Optional[str]   = Field(default=None, max_length=100)
    ai_estimated_biz_type: Optional[str]   = Field(default=None, max_length=100)
    ai_revenue_stage:      Optional[str]   = Field(default=None, max_length=50)
    ai_is_india_seller:    Optional[bool]  = None
    ai_is_fake_account:    Optional[bool]  = None
    ai_tags_json:          Optional[str]   = None
    ai_outreach_suggestion:Optional[str]   = None

    @field_validator("lead_status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f"lead_status must be one of {sorted(VALID_STATUSES)}")
        return v


class SellerLeadOut(BaseModel):
    id:                    str
    job_id:                Optional[str]
    username:              str
    source:                str
    profile_url:           Optional[str]
    full_name:             Optional[str]
    bio:                   Optional[str]
    website:               Optional[str]
    category:              Optional[str]
    profile_image_url:     Optional[str]
    followers_count:       Optional[int]
    following_count:       Optional[int]
    engagement_rate:       Optional[float]
    email:                 Optional[str]
    whatsapp:              Optional[str]
    country:               Optional[str]
    language:              Optional[str]
    ai_is_ecommerce:       Optional[bool]
    ai_relevance_score:    Optional[float]
    ai_confidence_score:   Optional[float]
    ai_category:           Optional[str]
    ai_estimated_biz_type: Optional[str]
    ai_revenue_stage:      Optional[str]
    ai_is_india_seller:    Optional[bool]
    ai_is_fake_account:    Optional[bool]
    ai_tags_json:          Optional[str]
    ai_outreach_suggestion:Optional[str]
    ai_classified_at:      Optional[str]
    lead_status:           str
    notes:                 Optional[str]
    tags_json:             Optional[str]
    discovery_source:      Optional[str]
    discovery_keyword:     Optional[str]
    last_scraped_at:       Optional[str]
    created_at:            str
    updated_at:            str


class LeadListFilters(BaseModel):
    source:        Optional[str]   = None
    country:       Optional[str]   = None
    category:      Optional[str]   = None
    lead_status:   Optional[str]   = None
    ai_score_min:  Optional[float] = Field(default=None, ge=0, le=1)
    ai_score_max:  Optional[float] = Field(default=None, ge=0, le=1)
    has_website:   Optional[bool]  = None
    has_email:     Optional[bool]  = None
    search:        Optional[str]   = Field(default=None, max_length=200)


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY JOB
# ─────────────────────────────────────────────────────────────────────────────

VALID_JOB_TYPES = {"hashtag", "competitor_followers", "direct"}
VALID_JOB_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}


class DiscoveryJobCreate(BaseModel):
    source:       str = Field(default="instagram", description="instagram | linkedin | …")
    job_type:     str = Field(..., description="hashtag | competitor_followers | direct")
    keyword:      str = Field(..., min_length=1, max_length=200)
    max_leads:    int = Field(default=500, ge=1, le=5000)
    keyword_id:   Optional[str] = None

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, v: str) -> str:
        if v not in VALID_JOB_TYPES:
            raise ValueError(f"job_type must be one of {sorted(VALID_JOB_TYPES)}")
        return v


class DiscoveryJobPatch(BaseModel):
    status: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        # Only cancel is allowed via API; other transitions are internal
        if v is not None and v not in {"cancelled"}:
            raise ValueError("Only 'cancelled' status is settable via API")
        return v


class DiscoveryJobOut(BaseModel):
    id:                 str
    keyword_id:         Optional[str]
    source:             str
    job_type:           str
    keyword:            str
    triggered_by:       str
    max_leads:          int
    status:             str
    leads_found:        int
    leads_created:      int
    leads_skipped_dupe: int
    leads_classified:   int
    started_at:         Optional[str]
    completed_at:       Optional[str]
    error_message:      Optional[str]
    created_at:         str
    updated_at:         str


# ─────────────────────────────────────────────────────────────────────────────
# DISCOVERY KEYWORD
# ─────────────────────────────────────────────────────────────────────────────

VALID_KEYWORD_TYPES = {"hashtag", "competitor", "direct"}


class DiscoveryKeywordCreate(BaseModel):
    keyword:      str = Field(..., min_length=1, max_length=200)
    keyword_type: str = Field(..., description="hashtag | competitor | direct")
    source:       str = Field(default="instagram")
    priority:     int = Field(default=5, ge=1, le=10)
    notes:        Optional[str] = None

    @field_validator("keyword_type")
    @classmethod
    def validate_keyword_type(cls, v: str) -> str:
        if v not in VALID_KEYWORD_TYPES:
            raise ValueError(f"keyword_type must be one of {sorted(VALID_KEYWORD_TYPES)}")
        return v


class DiscoveryKeywordPatch(BaseModel):
    is_active: Optional[bool] = None
    priority:  Optional[int]  = Field(default=None, ge=1, le=10)
    notes:     Optional[str]  = None


class DiscoveryKeywordOut(BaseModel):
    id:             str
    keyword:        str
    keyword_type:   str
    source:         str
    is_active:      bool
    priority:       int
    last_crawled_at:Optional[str]
    crawl_count:    int
    leads_found:    int
    notes:          Optional[str]
    created_at:     str
    updated_at:     str


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW (Phase 12)
# ─────────────────────────────────────────────────────────────────────────────

class ReviewPayload(BaseModel):
    """Payload for POST /leads/{id}/review."""
    action: str = Field(..., description="approve|reject|qualify|contact_ready|review|contacted")
    notes:  Optional[str] = Field(default=None, max_length=2000)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in VALID_REVIEW_ACTIONS:
            raise ValueError(f"action must be one of {sorted(VALID_REVIEW_ACTIONS)}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# OUTREACH (Phase 13)
# ─────────────────────────────────────────────────────────────────────────────

class OutreachPatch(BaseModel):
    """Payload for PATCH /leads/{id}/outreach."""
    outreach_status: Optional[str]  = None
    outreach_notes:  Optional[str]  = Field(default=None, max_length=2000)

    @field_validator("outreach_status")
    @classmethod
    def validate_outreach_status(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_OUTREACH_STATUSES:
            raise ValueError(f"outreach_status must be one of {sorted(VALID_OUTREACH_STATUSES)}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# BULK OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

class BulkClassifyRequest(BaseModel):
    """Optional filters for POST /leads/bulk-classify."""
    limit:  int = Field(default=50, ge=1, le=500, description="Max leads to classify")
    source: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVITY LOG (Phase 14)
# ─────────────────────────────────────────────────────────────────────────────

VALID_ACTIVITY_TYPES = {
    "note", "follow_up", "call_log", "email_log", "whatsapp_log",
    "tag", "status_change", "classify", "score", "outreach",
}


class ActivityCreate(BaseModel):
    """Payload for POST /leads/{id}/activity."""
    activity_type: str           = Field(..., description="note|follow_up|call_log|email_log|whatsapp_log|tag")
    content:       Optional[str] = Field(default=None, max_length=5000)
    metadata:      Optional[dict] = None
    follow_up_at:  Optional[datetime] = None   # only used when activity_type='follow_up'

    @field_validator("activity_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        allowed = {"note", "follow_up", "call_log", "email_log", "whatsapp_log", "tag"}
        if v not in allowed:
            raise ValueError(f"activity_type must be one of {sorted(allowed)}")
        return v


class ActivityOut(BaseModel):
    id:            str
    lead_id:       str
    activity_type: str
    icon:          str
    content:       Optional[str]
    metadata_json: Optional[dict]
    created_by:    str
    created_at:    str
