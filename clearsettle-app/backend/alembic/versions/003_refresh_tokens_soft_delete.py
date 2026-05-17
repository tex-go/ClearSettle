"""Add refresh_tokens table and soft-delete columns

Revision ID: 003
Revises: 002
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Soft-delete on users ──────────────────────────────────────────────────
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ── Soft-delete on companies ──────────────────────────────────────────────
    op.add_column("companies", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # SHA-256 hex digest of the plaintext token (never store plaintext)
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_index("ix_refresh_tokens_hash",    "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_user_id",         "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_expires_revoked", "refresh_tokens", ["expires_at", "revoked"])


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_column("companies", "deleted_at")
    op.drop_column("users",     "deleted_at")
