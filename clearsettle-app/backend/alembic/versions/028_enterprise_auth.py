"""Enterprise auth: password reset tokens, email verification tokens,
invitations, audit log, email_verified flag on users.

Revision ID: 028
Revises: 027
Create Date: 2026-05-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Soft-delete the demo user seeded in migration 002 ─────────────────────
    op.execute(
        sa.text(
            "UPDATE users SET deleted_at = NOW(), is_active = false "
            "WHERE email = 'demo@clearsettle.in'"
        )
    )

    # ── email_verified column on users ────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used",       sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_prt_user_id",    "password_reset_tokens", ["user_id"])
    op.create_index("ix_prt_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    # ── email_verification_tokens ─────────────────────────────────────────────
    op.create_table(
        "email_verification_tokens",
        sa.Column("id",         postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used",       sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_evt_user_id",    "email_verification_tokens", ["user_id"])
    op.create_index("ix_evt_token_hash", "email_verification_tokens", ["token_hash"], unique=True)

    # ── invitations ───────────────────────────────────────────────────────────
    op.create_table(
        "invitations",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invited_by",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("email",       sa.String(255), nullable=False),
        sa.Column("role",        sa.String(50),  nullable=False, server_default="member"),
        sa.Column("token_hash",  sa.String(128), nullable=False),
        sa.Column("expires_at",  sa.DateTime(),  nullable=False),
        sa.Column("accepted",    sa.Boolean(),   nullable=False, server_default="false"),
        sa.Column("created_at",  sa.DateTime(),  nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_inv_company_id",  "invitations", ["company_id"])
    op.create_index("ix_inv_email",       "invitations", ["email"])
    op.create_index("ix_inv_token_hash",  "invitations", ["token_hash"], unique=True)

    # ── audit_log_entries ─────────────────────────────────────────────────────
    op.create_table(
        "audit_log_entries",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action",      sa.String(100), nullable=False),
        sa.Column("resource",    sa.String(100)),
        sa.Column("resource_id", sa.String(255)),
        sa.Column("ip_address",  sa.String(45)),
        sa.Column("user_agent",  sa.Text()),
        sa.Column("metadata",    postgresql.JSONB(), nullable=True),
        sa.Column("created_at",  sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_ale_user_id",   "audit_log_entries", ["user_id"])
    op.create_index("ix_ale_action",    "audit_log_entries", ["action"])
    op.create_index("ix_ale_created_at","audit_log_entries", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log_entries")
    op.drop_table("invitations")
    op.drop_table("email_verification_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_column("users", "email_verified")
