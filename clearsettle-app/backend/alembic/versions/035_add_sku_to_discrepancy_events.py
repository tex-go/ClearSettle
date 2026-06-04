"""Add sku column to discrepancy_events.

Root cause: the DiscrepancyEvent ORM model defines sku = Column(String(200))
(discrepancy_event.py line 90) and reconciliation/seed.py writes to it, but
migration 007 (which created the table) never included the column.
All 29 migrations that followed also missed it.

Result: every SELECT on discrepancy_events raised
  asyncpg.exceptions.UndefinedColumnError: column discrepancy_events.sku does not exist

Fix: add the missing column with NULL default (no data loss, no downtime).

Revision ID: 035
Revises: 034
Create Date: 2026-06-04
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "discrepancy_events",
        sa.Column("sku", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("discrepancy_events", "sku")
