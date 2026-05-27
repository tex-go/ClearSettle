"""Store Amazon SP API app credentials in platform_connections (UI-configurable)

Previously sp_app_id and sp_redirect_uri were environment-only.
These two columns let each company store their own SP API app credentials
via the UI, removing the hard dependency on environment variables.

New columns on platform_connections:
    sp_app_id      — Amazon SP API Application ID (amzn1.sellerapps.app.xxx)
    sp_redirect_uri — OAuth redirect URI registered in Seller Central developer console

Both columns are nullable; when NULL the system falls back to environment variables
(SP_API_APP_ID / SP_API_REDIRECT_URI).  When set, the DB value takes precedence.

Revision ID: 011
Revises: 010
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("platform_connections",
                  sa.Column("sp_app_id",      sa.String(500), nullable=True))
    op.add_column("platform_connections",
                  sa.Column("sp_redirect_uri", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("platform_connections", "sp_redirect_uri")
    op.drop_column("platform_connections", "sp_app_id")
