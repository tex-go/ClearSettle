"""
038 — Social Accounts (Google, Instagram, and future providers)

Creates the social_accounts table for Identity Provider (IdP) integrations.
Also makes users.hashed_password nullable to support social-only accounts.

Architecture:
  One user can link N social accounts (one per provider).
  No schema changes needed to add new providers — provider is a free-form string.
  Tokens are Fernet-encrypted at rest.

Revision ID: 038
Revises:     037
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "038"
down_revision = "037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── social_accounts table ─────────────────────────────────────────────────
    op.create_table(
        "social_accounts",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",             postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),

        # Identity provider
        sa.Column("provider",             sa.String(50),  nullable=False),
        sa.Column("provider_user_id",     sa.String(255), nullable=False),
        sa.Column("provider_email",       sa.String(320), nullable=True),
        sa.Column("provider_name",        sa.String(255), nullable=True),
        sa.Column("profile_picture_url",  sa.Text,        nullable=True),
        sa.Column("provider_username",    sa.String(255), nullable=True),

        # Encrypted tokens
        sa.Column("access_token_enc",     sa.Text,        nullable=True),
        sa.Column("refresh_token_enc",    sa.Text,        nullable=True),
        sa.Column("token_expiry",         sa.DateTime,    nullable=True),
        sa.Column("token_scope",          sa.String(500), nullable=True),

        # Metadata
        sa.Column("is_primary",           sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("last_used_at",         sa.DateTime,    nullable=True),
        sa.Column("created_at",           sa.DateTime,    nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at",           sa.DateTime,    nullable=False,
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Unique: prevent two users from claiming the same IdP account
    op.create_unique_constraint(
        "uq_social_provider_user_id",
        "social_accounts",
        ["provider", "provider_user_id"],
    )

    # Indexes
    op.create_index("idx_social_user_id",      "social_accounts", ["user_id"])
    op.create_index("idx_social_provider",     "social_accounts", ["provider"])
    op.create_index("idx_social_user_provider","social_accounts", ["user_id", "provider"])

    # ── Make hashed_password nullable (social-only accounts have no password) ─
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE users SET hashed_password = 'REVERTED' WHERE hashed_password IS NULL")
    op.alter_column("users", "hashed_password", existing_type=sa.String(255), nullable=False)
    op.drop_index("idx_social_user_provider", table_name="social_accounts")
    op.drop_index("idx_social_provider",      table_name="social_accounts")
    op.drop_index("idx_social_user_id",       table_name="social_accounts")
    op.drop_constraint("uq_social_provider_user_id", "social_accounts", type_="unique")
    op.drop_table("social_accounts")
