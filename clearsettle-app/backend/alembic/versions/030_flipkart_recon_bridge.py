"""Phase 1: bridge FlipkartReconIssue → discrepancy_events.

Adds a nullable FK column `discrepancy_event_id` to `flipkart_recon_issues`
so that Flipkart file-parse discrepancies can be promoted into the unified
recovery workflow without losing their source data.

Strategy (non-destructive):
  1. Add nullable FK column — existing rows get NULL (not yet linked).
  2. Future Flipkart file parser writes a DiscrepancyEvent and backfills
     this FK when source='file_parse' and platform='flipkart'.
  3. Full data migration to consolidated table happens in Phase 2 (030→031).

Fix (v2): removed index=True from sa.Column to prevent Alembic from
auto-creating ix_flipkart_recon_issues_discrepancy_event_id before the
explicit op.create_index call.  Both ADD COLUMN and CREATE INDEX now use
IF NOT EXISTS to be idempotent on retry after a partial failure.

Revision ID: 030
Revises: 029
Create Date: 2026-05-28
"""
from __future__ import annotations

from alembic import op

revision = "030"
down_revision = "029"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── bridge FK: ADD COLUMN IF NOT EXISTS ──────────────────────────────────
    op.execute("""
        ALTER TABLE flipkart_recon_issues
        ADD COLUMN IF NOT EXISTS discrepancy_event_id UUID
            REFERENCES discrepancy_events(id) ON DELETE SET NULL
    """)

    # ── index for reverse lookup (CREATE INDEX IF NOT EXISTS) ─────────────────
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_flipkart_recon_issues_discrepancy_event_id
        ON flipkart_recon_issues (discrepancy_event_id)
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS ix_flipkart_recon_issues_discrepancy_event_id
    """)
    op.execute("""
        ALTER TABLE flipkart_recon_issues
        DROP COLUMN IF EXISTS discrepancy_event_id
    """)
