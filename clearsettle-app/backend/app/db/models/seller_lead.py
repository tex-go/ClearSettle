import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class DiscoveryKeyword(Base):
    """
    Seed keywords (hashtags, competitor usernames, categories) for crawl runs.

    Priority: 1 = highest, 10 = lowest.
    is_active = False to pause a keyword without deletion.
    """
    __tablename__ = "discovery_keywords"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    keyword      = Column(String(200), nullable=False)
    keyword_type = Column(String(30),  nullable=False)  # hashtag | competitor | direct
    source       = Column(String(50),  nullable=False, server_default="instagram")

    is_active  = Column(Boolean, default=True,  nullable=False)
    priority   = Column(Integer, default=5,     nullable=False)  # 1-10

    last_crawled_at = Column(DateTime, nullable=True)
    crawl_count     = Column(Integer,  default=0, nullable=False)
    leads_found     = Column(Integer,  default=0, nullable=False)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    jobs = relationship("DiscoveryJob", back_populates="keyword_ref", lazy="select")


class DiscoveryJob(Base):
    """
    One row per crawl run.

    Status lifecycle: queued → running → completed | failed
    Mirrors the SyncJob pattern — same fields, same status vocabulary.
    """
    __tablename__ = "discovery_jobs"

    id           = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    keyword_id   = Column(PG_UUID(as_uuid=True), ForeignKey("discovery_keywords.id", ondelete="SET NULL"), nullable=True, index=True)

    source       = Column(String(50),  nullable=False, server_default="instagram")
    job_type     = Column(String(50),  nullable=False)   # hashtag | competitor_followers | direct
    keyword      = Column(String(200), nullable=False)   # denormalised for display without JOIN
    triggered_by = Column(String(50),  nullable=False, server_default="manual")

    # Configuration
    max_leads = Column(Integer, default=500, nullable=False)

    # Status
    status = Column(String(30), nullable=False, server_default="queued", index=True)

    # Queue priority (1=highest, 10=lowest) and retry tracking
    priority    = Column(Integer, default=5,  nullable=False)
    retry_count = Column(Integer, default=0,  nullable=False)
    max_retries = Column(Integer, default=3,  nullable=False)

    # Progress counters
    leads_found        = Column(Integer, default=0, nullable=False)
    leads_created      = Column(Integer, default=0, nullable=False)
    leads_skipped_dupe = Column(Integer, default=0, nullable=False)
    leads_classified   = Column(Integer, default=0, nullable=False)

    # Timing
    started_at    = Column(DateTime, nullable=True)
    completed_at  = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    keyword_ref = relationship("DiscoveryKeyword", back_populates="jobs")
    leads       = relationship("SellerLead", back_populates="job", lazy="select")


class SellerLead(Base):
    """
    One row per discovered seller.

    Deduplication key: (username, source) — enforced by unique constraint.
    Status lifecycle: new → reviewing → qualified | rejected → contacted
    All AI fields are nullable; populated asynchronously by the classifier.
    """
    __tablename__ = "seller_leads"

    id  = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    job_id = Column(PG_UUID(as_uuid=True), ForeignKey("discovery_jobs.id", ondelete="SET NULL"), nullable=True, index=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    username    = Column(String(100),  nullable=False, index=True)
    source      = Column(String(50),   nullable=False, index=True)  # instagram | linkedin | …
    profile_url = Column(String(500),  nullable=True)

    # ── Public profile metadata ───────────────────────────────────────────────
    full_name         = Column(String(255), nullable=True)
    bio               = Column(Text,        nullable=True)
    website           = Column(String(500), nullable=True)
    category          = Column(String(100), nullable=True)
    profile_image_url = Column(String(500), nullable=True)

    followers_count = Column(Integer, nullable=True)
    following_count = Column(Integer, nullable=True)
    engagement_rate = Column(Numeric(6, 4), nullable=True)  # e.g. 0.0342

    # ── Contact info (public only) ────────────────────────────────────────────
    email     = Column(String(255), nullable=True)
    whatsapp  = Column(String(20),  nullable=True)

    # ── Geographic / linguistic ───────────────────────────────────────────────
    country  = Column(String(50), nullable=True)
    language = Column(String(20), nullable=True)

    # ── AI classification output ──────────────────────────────────────────────
    ai_is_ecommerce        = Column(Boolean,        nullable=True)
    ai_relevance_score     = Column(Numeric(4, 3),  nullable=True)  # 0.000 – 1.000
    ai_confidence_score    = Column(Numeric(4, 3),  nullable=True)
    ai_category            = Column(String(100),    nullable=True)  # d2c | marketplace | shopify …
    ai_estimated_biz_type  = Column(String(100),    nullable=True)
    ai_revenue_stage       = Column(String(50),     nullable=True)  # seed | growth | scale
    ai_is_india_seller     = Column(Boolean,        nullable=True)
    ai_is_fake_account     = Column(Boolean,        nullable=True)
    ai_tags_json           = Column(Text,           nullable=True)  # JSON array ["fashion","d2c"]
    ai_outreach_suggestion = Column(Text,           nullable=True)
    ai_classified_at       = Column(DateTime,       nullable=True)

    # ── Lead lifecycle ────────────────────────────────────────────────────────
    lead_status = Column(String(30), nullable=False, server_default="new", index=True)
    # new | review_pending | reviewing | approved | qualified | rejected | contact_ready | contacted | deleted

    notes     = Column(Text, nullable=True)
    tags_json = Column(Text, nullable=True)  # user-defined tags JSON array

    # ── Scoring (Phase 8) ─────────────────────────────────────────────────────
    lead_score           = Column(Numeric(5, 2), nullable=True)   # 0.00 – 100.00
    score_breakdown_json = Column(Text,          nullable=True)   # JSON factor dict
    priority_level       = Column(String(20),    nullable=True)   # hot | warm | cold | skip

    # ── Human review (Phase 12) ───────────────────────────────────────────────
    reviewed_at = Column(DateTime,    nullable=True)
    reviewed_by = Column(String(100), nullable=True)

    # ── Outreach preparation (Phase 13) ──────────────────────────────────────
    outreach_status = Column(String(30), nullable=True, server_default="pending")
    # pending | ready | contacted | skipped
    outreach_notes  = Column(Text, nullable=True)

    # ── CRM lifecycle (Phase 14) ──────────────────────────────────────────────
    follow_up_at = Column(DateTime,    nullable=True)   # next scheduled follow-up
    assigned_to  = Column(String(100), nullable=True)   # team member owning this lead

    # ── Discovery provenance ──────────────────────────────────────────────────
    discovery_source  = Column(String(50),  nullable=True)   # hashtag | competitor_followers | direct
    discovery_keyword = Column(String(200), nullable=True)   # e.g. "#ethnicwear"
    last_scraped_at   = Column(DateTime,    nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Deduplication: one lead per username per source
    __table_args__ = (
        UniqueConstraint("username", "source", name="uq_seller_lead_username_source"),
    )

    # Relationships
    job = relationship("DiscoveryJob", back_populates="leads")
