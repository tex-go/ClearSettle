"""Seller Discovery Engine — initial schema

New tables
----------
discovery_keywords
  Seed hashtags, competitor usernames, and categories queued for crawls.
  keyword_type: hashtag | competitor | direct
  is_active: false to pause without deletion.
  priority: 1 (highest) – 10 (lowest)

discovery_jobs
  One row per crawl run. Mirrors the sync_jobs lifecycle pattern exactly:
    queued → running → completed | failed
  Tracks per-run counters (found, created, dupe-skipped, classified).

seller_leads
  One row per discovered seller.
  Deduplication key: UNIQUE(username, source) — prevents duplicate scrapes.
  Status lifecycle: new → reviewing → qualified | rejected → contacted
  AI fields (ai_*) populated asynchronously by the classifier after scrape.

Indexes
-------
  ix_discovery_keywords_source_active    — fast active-keyword listing per source
  ix_discovery_jobs_status               — job queue polling
  ix_seller_leads_username               — quick dedup lookups
  ix_seller_leads_source                 — filter by source
  ix_seller_leads_lead_status            — CRM pipeline view
  ix_seller_leads_ai_relevance_score     — ranked lead queries
  ix_seller_leads_created_at             — time-series dashboard

Revision ID: 015
Revises: 014
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── discovery_keywords ────────────────────────────────────────────────────
    op.create_table(
        "discovery_keywords",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),

        sa.Column("keyword",      sa.String(200), nullable=False),
        sa.Column("keyword_type", sa.String(30),  nullable=False),  # hashtag|competitor|direct
        sa.Column("source",       sa.String(50),  nullable=False, server_default="instagram"),

        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority",  sa.Integer, nullable=False, server_default="5"),

        sa.Column("last_crawled_at", sa.DateTime, nullable=True),
        sa.Column("crawl_count",     sa.Integer,  nullable=False, server_default="0"),
        sa.Column("leads_found",     sa.Integer,  nullable=False, server_default="0"),

        sa.Column("notes", sa.Text, nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_discovery_keywords_source_active",
        "discovery_keywords", ["source", "is_active"],
    )

    # ── discovery_jobs ────────────────────────────────────────────────────────
    op.create_table(
        "discovery_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("keyword_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("discovery_keywords.id", ondelete="SET NULL"),
                  nullable=True),

        sa.Column("source",       sa.String(50),  nullable=False, server_default="instagram"),
        sa.Column("job_type",     sa.String(50),  nullable=False),
        sa.Column("keyword",      sa.String(200), nullable=False),
        sa.Column("triggered_by", sa.String(50),  nullable=False, server_default="manual"),

        sa.Column("max_leads", sa.Integer, nullable=False, server_default="500"),

        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),

        sa.Column("leads_found",        sa.Integer, nullable=False, server_default="0"),
        sa.Column("leads_created",      sa.Integer, nullable=False, server_default="0"),
        sa.Column("leads_skipped_dupe", sa.Integer, nullable=False, server_default="0"),
        sa.Column("leads_classified",   sa.Integer, nullable=False, server_default="0"),

        sa.Column("started_at",    sa.DateTime, nullable=True),
        sa.Column("completed_at",  sa.DateTime, nullable=True),
        sa.Column("error_message", sa.Text,     nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_discovery_jobs_status",     "discovery_jobs", ["status"])
    op.create_index("ix_discovery_jobs_keyword_id", "discovery_jobs", ["keyword_id"])

    # ── seller_leads ──────────────────────────────────────────────────────────
    op.create_table(
        "seller_leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("discovery_jobs.id", ondelete="SET NULL"),
                  nullable=True),

        # Identity
        sa.Column("username",    sa.String(100), nullable=False),
        sa.Column("source",      sa.String(50),  nullable=False),
        sa.Column("profile_url", sa.String(500), nullable=True),

        # Public profile metadata
        sa.Column("full_name",         sa.String(255), nullable=True),
        sa.Column("bio",               sa.Text,        nullable=True),
        sa.Column("website",           sa.String(500), nullable=True),
        sa.Column("category",          sa.String(100), nullable=True),
        sa.Column("profile_image_url", sa.String(500), nullable=True),

        sa.Column("followers_count", sa.Integer,         nullable=True),
        sa.Column("following_count", sa.Integer,         nullable=True),
        sa.Column("engagement_rate", sa.Numeric(6, 4),   nullable=True),

        # Contact info (public only)
        sa.Column("email",    sa.String(255), nullable=True),
        sa.Column("whatsapp", sa.String(20),  nullable=True),

        # Geographic / linguistic
        sa.Column("country",  sa.String(50), nullable=True),
        sa.Column("language", sa.String(20), nullable=True),

        # AI classification
        sa.Column("ai_is_ecommerce",        sa.Boolean,      nullable=True),
        sa.Column("ai_relevance_score",     sa.Numeric(4,3), nullable=True),
        sa.Column("ai_confidence_score",    sa.Numeric(4,3), nullable=True),
        sa.Column("ai_category",            sa.String(100),  nullable=True),
        sa.Column("ai_estimated_biz_type",  sa.String(100),  nullable=True),
        sa.Column("ai_revenue_stage",       sa.String(50),   nullable=True),
        sa.Column("ai_is_india_seller",     sa.Boolean,      nullable=True),
        sa.Column("ai_is_fake_account",     sa.Boolean,      nullable=True),
        sa.Column("ai_tags_json",           sa.Text,         nullable=True),
        sa.Column("ai_outreach_suggestion", sa.Text,         nullable=True),
        sa.Column("ai_classified_at",       sa.DateTime,     nullable=True),

        # Lead lifecycle
        sa.Column("lead_status", sa.String(30), nullable=False, server_default="new"),
        sa.Column("notes",       sa.Text,       nullable=True),
        sa.Column("tags_json",   sa.Text,       nullable=True),

        # Discovery provenance
        sa.Column("discovery_source",  sa.String(50),  nullable=True),
        sa.Column("discovery_keyword", sa.String(200), nullable=True),
        sa.Column("last_scraped_at",   sa.DateTime,    nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),

        # Deduplication constraint
        sa.UniqueConstraint("username", "source", name="uq_seller_lead_username_source"),
    )
    op.create_index("ix_seller_leads_username",          "seller_leads", ["username"])
    op.create_index("ix_seller_leads_source",            "seller_leads", ["source"])
    op.create_index("ix_seller_leads_lead_status",       "seller_leads", ["lead_status"])
    op.create_index("ix_seller_leads_ai_relevance_score","seller_leads", ["ai_relevance_score"])
    op.create_index("ix_seller_leads_created_at",        "seller_leads", ["created_at"])
    op.create_index("ix_seller_leads_job_id",            "seller_leads", ["job_id"])


def downgrade() -> None:
    op.drop_table("seller_leads")
    op.drop_table("discovery_jobs")
    op.drop_table("discovery_keywords")
