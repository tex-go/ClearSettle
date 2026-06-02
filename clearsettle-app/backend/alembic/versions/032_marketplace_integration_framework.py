"""Marketplace Integration Framework — core schema.

Creates 8 new tables that form the universal marketplace connector layer.
Existing platform_connections table is untouched for backward compatibility.

Tables
------
marketplaces             — static registry of supported platforms
marketplace_connections  — per-company connection to a marketplace
marketplace_credentials  — Fernet-encrypted credentials (isolated table)
marketplace_accounts     — account info fetched from marketplace APIs
marketplace_sync_jobs    — sync job lifecycle tracking
marketplace_sync_logs    — structured per-job event logs
oauth_states             — short-lived CSRF state tokens
marketplace_audit_logs   — immutable audit trail

Revision ID: 032
Revises: 031
Create Date: 2026-05-31
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "032"
down_revision = "031"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ── marketplaces ───────────────────────────────────────────────────────────
    op.create_table(
        "marketplaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name",        sa.String(100),  nullable=False),
        sa.Column("slug",        sa.String(50),   nullable=False),
        sa.Column("connection_type", sa.String(50), nullable=False),
        # oauth | api_key | api_key_secret | username_password | manual_upload | partner_api
        sa.Column("logo_url",    sa.Text(),       nullable=True),
        sa.Column("website_url", sa.Text(),       nullable=True),
        sa.Column("description", sa.Text(),       nullable=True),
        sa.Column("docs_url",    sa.Text(),       nullable=True),
        sa.Column("is_active",   sa.Boolean(),    nullable=False, server_default=sa.text("TRUE")),
        sa.Column("is_live",     sa.Boolean(),    nullable=False, server_default=sa.text("FALSE")),
        # is_live = False means "coming soon" (UI shows disabled state)
        sa.Column("required_credential_fields", postgresql.JSONB(), nullable=True),
        # e.g. ["consumer_key", "consumer_secret"] for WooCommerce
        sa.Column("oauth_scopes",    sa.Text(),      nullable=True),
        sa.Column("oauth_auth_url",  sa.Text(),      nullable=True),
        sa.Column("oauth_token_url", sa.Text(),      nullable=True),
        sa.Column("region_support",  postgresql.JSONB(), nullable=True),
        # e.g. {"IN": "India", "US": "United States"}
        sa.Column("sort_order",  sa.Integer(),    nullable=False, server_default=sa.text("0")),
        sa.Column("meta",        postgresql.JSONB(), nullable=True),
        sa.Column("created_at",  sa.DateTime(),   nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",  sa.DateTime(),   nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_marketplaces_slug",      "marketplaces", ["slug"],      unique=True)
    op.create_index("ix_marketplaces_is_active", "marketplaces", ["is_active"])

    # ── marketplace_connections ────────────────────────────────────────────────
    op.create_table(
        "marketplace_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("marketplace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("connection_type", sa.String(50), nullable=False),
        sa.Column("status",          sa.String(50), nullable=False,
                  server_default=sa.text("'disconnected'")),
        # disconnected | connecting | connected | error | suspended | revoked
        sa.Column("display_name",   sa.String(255), nullable=True),
        sa.Column("seller_name",    sa.String(255), nullable=True),
        sa.Column("seller_email",   sa.String(255), nullable=True),
        sa.Column("seller_id",      sa.String(255), nullable=True),
        # their ID on the marketplace (e.g. selling_partner_id for Amazon)
        sa.Column("region",         sa.String(50),  nullable=True),
        sa.Column("shop_domain",    sa.String(255), nullable=True),
        # Shopify: store.myshopify.com subdomain
        # ── Sync tracking ────────────────────────────────────────────────────
        sa.Column("last_sync_at",     sa.DateTime(),  nullable=True),
        sa.Column("last_sync_status", sa.String(50),  nullable=True),
        sa.Column("last_sync_error",  sa.Text(),      nullable=True),
        sa.Column("total_syncs",      sa.Integer(),   nullable=False, server_default=sa.text("0")),
        # ── Lifecycle ─────────────────────────────────────────────────────────
        sa.Column("connected_at",    sa.DateTime(),  nullable=True),
        sa.Column("disconnected_at", sa.DateTime(),  nullable=True),
        sa.Column("error_message",   sa.Text(),      nullable=True),
        sa.Column("deleted_at",      sa.DateTime(),  nullable=True),
        sa.Column("created_at",      sa.DateTime(),  nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at",      sa.DateTime(),  nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint("company_id", "marketplace_id", name="uq_company_marketplace"),
    )
    op.create_index("ix_mc_company_id",     "marketplace_connections", ["company_id"])
    op.create_index("ix_mc_marketplace_id", "marketplace_connections", ["marketplace_id"])
    op.create_index("ix_mc_status",         "marketplace_connections", ["status"])
    op.create_index("ix_mc_deleted_at",     "marketplace_connections", ["deleted_at"])

    # ── marketplace_credentials ────────────────────────────────────────────────
    op.create_table(
        "marketplace_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        # ── Encrypted fields (Fernet) — columns ending _enc are NEVER plaintext ──
        sa.Column("access_token_enc",  sa.Text(), nullable=True),
        sa.Column("refresh_token_enc", sa.Text(), nullable=True),
        sa.Column("client_id_enc",     sa.Text(), nullable=True),
        sa.Column("client_secret_enc", sa.Text(), nullable=True),
        sa.Column("api_key_enc",       sa.Text(), nullable=True),
        sa.Column("api_secret_enc",    sa.Text(), nullable=True),
        sa.Column("username_enc",      sa.Text(), nullable=True),
        sa.Column("password_enc",      sa.Text(), nullable=True),
        sa.Column("extra_enc",         sa.Text(), nullable=True),
        # JSON blob for platform-specific additional credentials
        # ── Expiry tracking ───────────────────────────────────────────────────
        sa.Column("access_token_expires_at",  sa.DateTime(), nullable=True),
        sa.Column("refresh_token_expires_at", sa.DateTime(), nullable=True),
        # ── Display only (non-sensitive) ──────────────────────────────────────
        sa.Column("api_key_display", sa.String(50), nullable=True),
        # masked: "FKMT****9ABC"
        sa.Column("scope",           sa.Text(),     nullable=True),
        # scopes granted during OAuth
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mkcred_connection_id", "marketplace_credentials", ["connection_id"])

    # ── marketplace_accounts ───────────────────────────────────────────────────
    op.create_table(
        "marketplace_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("account_id",    sa.String(255), nullable=True),
        sa.Column("account_name",  sa.String(500), nullable=True),
        sa.Column("account_email", sa.String(255), nullable=True),
        sa.Column("account_type",  sa.String(100), nullable=True),
        # individual | professional | business
        sa.Column("region",        sa.String(50),  nullable=True),
        sa.Column("country",       sa.String(100), nullable=True),
        sa.Column("currency",      sa.String(10),  nullable=True),
        sa.Column("marketplace_data", postgresql.JSONB(), nullable=True),
        # raw account payload from marketplace API
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mkacc_connection_id", "marketplace_accounts", ["connection_id"])

    # ── marketplace_sync_jobs ──────────────────────────────────────────────────
    op.create_table(
        "marketplace_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("sync_type", sa.String(100), nullable=False),
        # orders | settlements | fees | taxes | inventory | reports | full
        sa.Column("status", sa.String(50), nullable=False,
                  server_default=sa.text("'queued'")),
        # queued | running | completed | failed | cancelled
        sa.Column("triggered_by",  sa.String(255), nullable=True),
        # user_id (UUID as string) | "scheduler" | "webhook"
        sa.Column("date_from",     sa.DateTime(),  nullable=True),
        sa.Column("date_to",       sa.DateTime(),  nullable=True),
        sa.Column("started_at",    sa.DateTime(),  nullable=True),
        sa.Column("completed_at",  sa.DateTime(),  nullable=True),
        sa.Column("items_synced",  sa.Integer(),   nullable=False, server_default=sa.text("0")),
        sa.Column("items_failed",  sa.Integer(),   nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(),      nullable=True),
        sa.Column("meta",          postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mksj_connection_id", "marketplace_sync_jobs", ["connection_id"])
    op.create_index("ix_mksj_status",        "marketplace_sync_jobs", ["status"])
    op.create_index("ix_mksj_created_at",    "marketplace_sync_jobs", ["created_at"])

    # ── marketplace_sync_logs ──────────────────────────────────────────────────
    op.create_table(
        "marketplace_sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("sync_job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_sync_jobs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_connections.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("log_level", sa.String(20), nullable=False, server_default=sa.text("'info'")),
        sa.Column("event",     sa.String(200), nullable=False),
        sa.Column("message",   sa.Text(),      nullable=True),
        sa.Column("extra",     postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mksl_sync_job_id",   "marketplace_sync_logs", ["sync_job_id"])
    op.create_index("ix_mksl_connection_id", "marketplace_sync_logs", ["connection_id"])

    # ── oauth_states ───────────────────────────────────────────────────────────
    op.create_table(
        "oauth_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("marketplace_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state_token",  sa.String(255), nullable=False, unique=True),
        sa.Column("redirect_uri", sa.Text(),      nullable=True),
        sa.Column("extra_params", postgresql.JSONB(), nullable=True),
        sa.Column("expires_at",   sa.DateTime(),  nullable=False),
        sa.Column("used_at",      sa.DateTime(),  nullable=True),
        sa.Column("created_at",   sa.DateTime(),  nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_os_state_token",  "oauth_states", ["state_token"])
    op.create_index("ix_os_company_id",   "oauth_states", ["company_id"])
    op.create_index("ix_os_expires_at",   "oauth_states", ["expires_at"])

    # ── marketplace_audit_logs ─────────────────────────────────────────────────
    op.create_table(
        "marketplace_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("marketplace_connections.id", ondelete="SET NULL"),
                  nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action",     sa.String(200), nullable=False),
        # connection.created | connection.connected | connection.disconnected
        # sync.started | sync.completed | sync.failed
        # credential.updated | oauth.initiated | oauth.callback
        sa.Column("old_value",  postgresql.JSONB(), nullable=True),
        sa.Column("new_value",  postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(50),      nullable=True),
        sa.Column("user_agent", sa.Text(),           nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_mkal_company_id",    "marketplace_audit_logs", ["company_id"])
    op.create_index("ix_mkal_connection_id", "marketplace_audit_logs", ["connection_id"])
    op.create_index("ix_mkal_created_at",    "marketplace_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("marketplace_audit_logs")
    op.drop_table("oauth_states")
    op.drop_table("marketplace_sync_logs")
    op.drop_table("marketplace_sync_jobs")
    op.drop_table("marketplace_accounts")
    op.drop_table("marketplace_credentials")
    op.drop_table("marketplace_connections")
    op.drop_table("marketplaces")
