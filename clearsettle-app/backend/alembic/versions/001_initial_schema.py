"""Initial schema: users, companies, platform_connections, sync_jobs

Revision ID: 001
Revises:
Create Date: 2026-05-17
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.Column("role", sa.String(50), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── companies ────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("gstin", sa.String(20)),
        sa.Column("city", sa.String(100)),
        sa.Column("industry", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_companies_user_id", "companies", ["user_id"])

    # ── platform_connections ─────────────────────────────────────────────────
    op.create_table(
        "platform_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),

        # LWA app credentials
        sa.Column("sp_client_id", sa.String(500)),
        sa.Column("sp_client_secret_enc", sa.Text()),

        # Per-seller OAuth tokens
        sa.Column("sp_refresh_token_enc", sa.Text()),
        sa.Column("sp_access_token_enc", sa.Text()),
        sa.Column("sp_access_token_expires_at", sa.DateTime()),

        # Seller identity
        sa.Column("sp_selling_partner_id", sa.String(255)),
        sa.Column("sp_marketplace_id", sa.String(50)),
        sa.Column("sp_region", sa.String(10), server_default="eu"),
        sa.Column("sp_endpoint", sa.String(200),
                  server_default="https://sellingpartnerapi-eu.amazon.com"),

        # OAuth CSRF state
        sa.Column("oauth_state", sa.String(255)),

        # Generic fields (non-SP-API platforms)
        sa.Column("api_key_display", sa.String(50)),
        sa.Column("webhook_secret_enc", sa.Text()),

        # Sync tracking
        sa.Column("last_sync_at", sa.DateTime()),
        sa.Column("last_sync_error", sa.Text()),
        sa.Column("total_orders_synced", sa.Integer(), server_default="0"),

        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),

        sa.UniqueConstraint("company_id", "platform", name="uq_company_platform"),
    )
    op.create_index("ix_pc_company_id", "platform_connections", ["company_id"])
    op.create_index("ix_pc_status", "platform_connections", ["status"])

    # ── sync_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_connections.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime()),
        sa.Column("completed_at", sa.DateTime()),
        sa.Column("error_message", sa.Text()),
        sa.Column("records_synced", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_sj_connection_id", "sync_jobs", ["connection_id"])
    op.create_index("ix_sj_status", "sync_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("sync_jobs")
    op.drop_table("platform_connections")
    op.drop_table("companies")
    op.drop_table("users")
