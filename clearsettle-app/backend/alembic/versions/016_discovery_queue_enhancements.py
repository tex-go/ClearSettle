"""Discovery queue enhancements — retry + priority columns

Adds three columns to discovery_jobs:
  priority     INT NOT NULL DEFAULT 5   — queue ordering (1=highest, 10=lowest)
  retry_count  INT NOT NULL DEFAULT 0   — how many times this job has been retried
  max_retries  INT NOT NULL DEFAULT 3   — maximum retries before terminal failure

Revision ID: 016
Revises: 015
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("discovery_jobs", sa.Column("priority",    sa.Integer(), nullable=False, server_default="5"))
    op.add_column("discovery_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("discovery_jobs", sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"))
    op.create_index("ix_discovery_jobs_priority", "discovery_jobs", ["priority"])


def downgrade() -> None:
    op.drop_index("ix_discovery_jobs_priority", "discovery_jobs")
    op.drop_column("discovery_jobs", "max_retries")
    op.drop_column("discovery_jobs", "retry_count")
    op.drop_column("discovery_jobs", "priority")
