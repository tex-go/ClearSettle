"""Add generic credential columns to platform_connections

New columns
-----------
credentials_enc     TEXT        — Fernet-encrypted JSON of platform API credentials
                                  e.g. {"api_key": "...", "api_secret": "..."}
platform_seller_id  VARCHAR(255)— Generic seller / merchant ID for non-Amazon platforms
webhook_url         VARCHAR(500)— Webhook callback URL registered with the platform

These columns extend the existing SP-API-specific columns (sp_*) which remain
for Amazon OAuth.  All non-Amazon platforms use credentials_enc.

Revision ID: 004
Revises: 003
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "platform_connections",
        sa.Column("credentials_enc", sa.Text(), nullable=True),
    )
    op.add_column(
        "platform_connections",
        sa.Column("platform_seller_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "platform_connections",
        sa.Column("webhook_url", sa.String(500), nullable=True),
    )

    # Composite index for fast filtering by platform + status (used in list queries)
    op.create_index(
        "ix_pc_platform_status",
        "platform_connections",
        ["platform", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_pc_platform_status", table_name="platform_connections")
    op.drop_column("platform_connections", "webhook_url")
    op.drop_column("platform_connections", "platform_seller_id")
    op.drop_column("platform_connections", "credentials_enc")
