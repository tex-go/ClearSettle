"""Seed marketplace registry and super-admin account.

Super-admin credentials are read EXCLUSIVELY from environment variables:
  SUPER_ADMIN_EMAIL    (default: Admin@clearsettle.com)
  SUPER_ADMIN_PASSWORD (default: Admin@123)

The password default is intentionally weak — operators MUST override
SUPER_ADMIN_PASSWORD in production before running migrations.

Revision ID: 033
Revises: 032
Create Date: 2026-05-31
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

revision = "033"
down_revision = "032"
branch_labels = None
depends_on = None

# ── Marketplace catalog ────────────────────────────────────────────────────────

MARKETPLACE_SEED = [
    {
        "slug": "amazon",
        "name": "Amazon",
        "connection_type": "oauth",
        "description": "Connect your Amazon Seller Central account via SP-API OAuth.",
        "website_url": "https://sell.amazon.in",
        "docs_url": "https://developer-docs.amazon.com/sp-api",
        "is_live": True,
        "required_credential_fields": None,
        "oauth_scopes": "sellingpartnerapi::orders:read sellingpartnerapi::finances:read",
        "oauth_auth_url": "https://sellercentral.amazon.in/apps/authorize/consent",
        "oauth_token_url": "https://api.amazon.com/auth/o2/token",
        "region_support": {"IN": "India", "US": "United States", "UK": "United Kingdom", "EU": "Europe"},
        "sort_order": 1,
        "meta": {"sp_api": True, "lwa": True},
    },
    {
        "slug": "flipkart",
        "name": "Flipkart",
        "connection_type": "manual_upload",
        "description": "Upload Flipkart settlement and P&L reports for reconciliation.",
        "website_url": "https://seller.flipkart.com",
        "docs_url": "https://seller.flipkart.com/api-docs/FMSAPI.html",
        "is_live": True,
        "required_credential_fields": None,
        "oauth_scopes": None,
        "region_support": {"IN": "India"},
        "sort_order": 2,
        "meta": {"manual_upload": True, "future_oauth": True},
    },
    {
        "slug": "shopify",
        "name": "Shopify",
        "connection_type": "oauth",
        "description": "Connect your Shopify store via OAuth to sync orders and financials.",
        "website_url": "https://www.shopify.com",
        "docs_url": "https://shopify.dev/docs/api/admin-rest",
        "is_live": True,
        "required_credential_fields": None,
        "oauth_scopes": "read_orders,read_finances,read_products,read_inventory",
        "oauth_auth_url": "https://{shop}.myshopify.com/admin/oauth/authorize",
        "oauth_token_url": "https://{shop}.myshopify.com/admin/oauth/access_token",
        "region_support": {"GLOBAL": "Global"},
        "sort_order": 3,
        "meta": {"shop_specific": True},
    },
    {
        "slug": "woocommerce",
        "name": "WooCommerce",
        "connection_type": "api_key_secret",
        "description": "Connect your WooCommerce store using Consumer Key and Consumer Secret.",
        "website_url": "https://woocommerce.com",
        "docs_url": "https://woocommerce.github.io/woocommerce-rest-api-docs",
        "is_live": True,
        "required_credential_fields": ["store_url", "consumer_key", "consumer_secret"],
        "sort_order": 4,
        "meta": {"self_hosted": True},
    },
    {
        "slug": "meesho",
        "name": "Meesho",
        "connection_type": "manual_upload",
        "description": "Upload Meesho settlement reports for reconciliation.",
        "website_url": "https://supplier.meesho.com",
        "is_live": True,
        "required_credential_fields": None,
        "region_support": {"IN": "India"},
        "sort_order": 5,
        "meta": {"manual_upload": True},
    },
    {
        "slug": "myntra",
        "name": "Myntra",
        "connection_type": "manual_upload",
        "description": "Upload Myntra settlement reports for reconciliation.",
        "website_url": "https://partner.myntra.com",
        "is_live": True,
        "required_credential_fields": None,
        "region_support": {"IN": "India"},
        "sort_order": 6,
        "meta": {"manual_upload": True},
    },
    {
        "slug": "ajio",
        "name": "AJIO",
        "connection_type": "manual_upload",
        "description": "Upload AJIO settlement reports for reconciliation.",
        "website_url": "https://www.ajio.com/seller",
        "is_live": True,
        "required_credential_fields": None,
        "region_support": {"IN": "India"},
        "sort_order": 7,
        "meta": {"manual_upload": True},
    },
    {
        "slug": "jiomart",
        "name": "JioMart",
        "connection_type": "manual_upload",
        "description": "Upload JioMart settlement reports for reconciliation.",
        "website_url": "https://jiomartpartners.com",
        "is_live": False,
        "required_credential_fields": None,
        "region_support": {"IN": "India"},
        "sort_order": 8,
        "meta": {"manual_upload": True},
    },
    {
        "slug": "ebay",
        "name": "eBay",
        "connection_type": "oauth",
        "description": "Connect your eBay seller account via OAuth.",
        "website_url": "https://www.ebay.com/sl/sell",
        "docs_url": "https://developer.ebay.com/api-docs",
        "is_live": False,
        "oauth_scopes": "https://api.ebay.com/oauth/api_scope/sell.finances",
        "sort_order": 9,
        "meta": {},
    },
    {
        "slug": "walmart",
        "name": "Walmart Marketplace",
        "connection_type": "api_key_secret",
        "description": "Connect your Walmart Marketplace seller account.",
        "website_url": "https://seller.walmart.com",
        "docs_url": "https://developer.walmart.com",
        "is_live": False,
        "required_credential_fields": ["client_id", "client_secret"],
        "sort_order": 10,
        "meta": {},
    },
    {
        "slug": "etsy",
        "name": "Etsy",
        "connection_type": "oauth",
        "description": "Connect your Etsy shop via OAuth.",
        "website_url": "https://www.etsy.com/sell",
        "docs_url": "https://developers.etsy.com/documentation",
        "is_live": False,
        "oauth_scopes": "transactions_r listings_r shops_r",
        "sort_order": 11,
        "meta": {},
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    now  = datetime.utcnow()

    # ── Ensure is_superadmin column exists on users table ─────────────────────
    # This column is required by the super-admin seed below but was not present
    # in the initial users table schema — add it idempotently.
    bind.execute(sa.text("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_superadmin BOOLEAN NOT NULL DEFAULT FALSE
    """))

    # ── Seed marketplace registry ──────────────────────────────────────────────
    for row in MARKETPLACE_SEED:
        mid = str(uuid.uuid4())
        # JSONB columns: pass JSON strings + use ::jsonb cast in SQL.
        # asyncpg expects plain Python values in bind params — NOT SQLAlchemy
        # Cast/expression objects. json.dumps() serialises dicts/lists to
        # strings; PostgreSQL casts them to JSONB server-side via ::jsonb.
        rcf  = row.get("required_credential_fields")
        rsup = row.get("region_support")
        meta = row.get("meta", {})

        bind.execute(
            sa.text("""
                INSERT INTO marketplaces (
                    id, name, slug, connection_type,
                    description, website_url, docs_url,
                    is_active, is_live,
                    required_credential_fields, oauth_scopes,
                    oauth_auth_url, oauth_token_url,
                    region_support, sort_order, meta,
                    created_at, updated_at
                ) VALUES (
                    :id, :name, :slug, :connection_type,
                    :description, :website_url, :docs_url,
                    :is_active, :is_live,
                    CAST(:required_credential_fields AS jsonb),
                    :oauth_scopes,
                    :oauth_auth_url, :oauth_token_url,
                    CAST(:region_support AS jsonb),
                    :sort_order,
                    CAST(:meta AS jsonb),
                    :created_at, :updated_at
                ) ON CONFLICT (slug) DO NOTHING
            """),
            {
                "id":                         mid,
                "name":                       row["name"],
                "slug":                       row["slug"],
                "connection_type":            row["connection_type"],
                "description":                row.get("description"),
                "website_url":                row.get("website_url"),
                "docs_url":                   row.get("docs_url"),
                "is_active":                  True,
                "is_live":                    row.get("is_live", False),
                # Plain JSON strings — asyncpg sends as text, Postgres casts
                "required_credential_fields": json.dumps(rcf)  if rcf  is not None else "null",
                "oauth_scopes":               row.get("oauth_scopes"),
                "oauth_auth_url":             row.get("oauth_auth_url"),
                "oauth_token_url":            row.get("oauth_token_url"),
                "region_support":             json.dumps(rsup) if rsup is not None else "null",
                "sort_order":                 row.get("sort_order", 0),
                "meta":                       json.dumps(meta),
                "created_at":                 now,
                "updated_at":                 now,
            }
        )

    # ── Seed super admin ───────────────────────────────────────────────────────
    admin_email    = os.environ.get("SUPER_ADMIN_EMAIL",    "Admin@clearsettle.com")
    admin_password = os.environ.get("SUPER_ADMIN_PASSWORD", "Admin@123")
    admin_name     = os.environ.get("SUPER_ADMIN_NAME",     "ClearSettle Admin")

    if admin_email == "Admin@clearsettle.com" and admin_password == "Admin@123":
        logger.warning(
            "\n"
            "╔═══════════════════════════════════════════════════════════════════╗\n"
            "║  WARNING: Super admin uses DEFAULT credentials.                   ║\n"
            "║  Set SUPER_ADMIN_EMAIL and SUPER_ADMIN_PASSWORD in .env           ║\n"
            "║  BEFORE running this migration in production.                     ║\n"
            "╚═══════════════════════════════════════════════════════════════════╝"
        )

    # Hash password using bcrypt (same algorithm as the app's auth layer)
    try:
        from passlib.context import CryptContext
        ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = ctx.hash(admin_password)
    except ImportError:
        import hashlib
        import hmac
        hashed_password = hashlib.sha256(admin_password.encode()).hexdigest()
        logger.warning("passlib not available — password hashed with SHA-256 (not recommended for production)")

    admin_id      = str(uuid.uuid4())
    admin_company_id = str(uuid.uuid4())

    # Check if super admin already exists
    existing = bind.execute(
        sa.text("SELECT id FROM users WHERE email = :email"),
        {"email": admin_email}
    ).fetchone()

    if existing:
        logger.info("Super admin %s already exists — skipping seed.", admin_email)
        return

    # Create super admin user first (company needs user_id FK)
    bind.execute(
        sa.text("""
            INSERT INTO users (
                id, email, hashed_password, name,
                is_active, email_verified, is_superadmin,
                created_at, updated_at
            ) VALUES (
                :id, :email, :password, :name,
                TRUE, TRUE, TRUE,
                :now, :now
            ) ON CONFLICT (email) DO NOTHING
        """),
        {
            "id":       admin_id,
            "email":    admin_email,
            "password": hashed_password,
            "name":     admin_name,
            "now":      now,
        },
    )

    # Create admin company with user_id (NOT NULL FK to users)
    bind.execute(
        sa.text("""
            INSERT INTO companies (id, user_id, name, created_at, updated_at)
            VALUES (:id, :user_id, :name, :now, :now)
            ON CONFLICT DO NOTHING
        """),
        {"id": admin_company_id, "user_id": admin_id, "name": "ClearSettle Platform", "now": now},
    )

    logger.info("Super admin seeded: %s", admin_email)


def downgrade() -> None:
    bind = op.get_bind()
    admin_email = os.environ.get("SUPER_ADMIN_EMAIL", "Admin@clearsettle.com")

    # Remove marketplace seeds
    for row in MARKETPLACE_SEED:
        bind.execute(
            sa.text("DELETE FROM marketplaces WHERE slug = :slug"),
            {"slug": row["slug"]},
        )

    # Remove super admin (only if created by this migration)
    bind.execute(
        sa.text("DELETE FROM users WHERE email = :email AND is_superadmin = TRUE"),
        {"email": admin_email},
    )
