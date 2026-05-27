"""Phase 1: bridge FlipkartReconIssue → discrepancy_events.

Adds a nullable FK column `discrepancy_event_id` to `flipkart_recon_issues`
so that Flipkart file-parse discrepancies can be promoted into the unified
recovery workflow without losing their source data.

Strategy (non-destructive):
  1. Add nullable FK column — existing rows get NULL (not yet linked).
  2. Future Flipkart file parser writes a DiscrepancyEvent and backfills
     this FK when source='file_parse' and platform='flipkart'.
  3. Full data migration to consolidated table happens in Phase 2 (030→031).

Revision ID: 030
Revises: 029
Create Date: 2026-05-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── bridge FK ─────────────────────────────────────────────────────────────
    op.add_column(
        "flipkart_recon_issues",
        sa.Column(
            "discrepancy_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("discrepancy_events.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    # ── index for reverse lookup: discrepancy_event → flipkart issue ──────────
    op.create_index(
        "ix_flipkart_recon_issues_discrepancy_event_id",
        "flipkart_recon_issues",
        ["discrepancy_event_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_flipkart_recon_issues_discrepancy_event_id",
        "flipkart_recon_issues",
    )
    op.drop_column("flipkart_recon_issues", "discrepancy_event_id")
