"""
037 — Idempotency + Event Versioning (Architecture Hardening)

Pre-Amazon SP API hardening pass.  Adds the fields required for:
  1. Idempotent inserts from API connectors  (external_event_id)
  2. Schema evolution without ETL changes    (event_version)

These changes are BACKWARD COMPATIBLE:
  - Both new columns are nullable.
  - All existing rows are back-filled with sensible defaults.
  - No ETL, dashboard, or analytics code reads these columns.
  - Only LedgerSyncExecutor uses external_event_id (ON CONFLICT DO NOTHING).

Changes to ingestion_ledger:
  + external_event_id  VARCHAR(500)  nullable  — platform-native event ID
                                                  e.g. "{order_id}::{item_id}::Principal::sale"
  + event_version      VARCHAR(10)   nullable  — "1.0" or "1.1"

  UNIQUE INDEX  uq_ledger_file_event
    ON (uploaded_file_id, external_event_id)
    WHERE external_event_id IS NOT NULL
    — partial unique index: only deduplicates rows that have an external_event_id

WHY PARTIAL UNIQUE?
  Manual upload rows (pre-1.1, no external_event_id) must not be affected.
  API connector rows (1.1+, always have external_event_id) are deduplicated.
  This way old data and new data coexist without constraint violations.

Revision ID: 037
Revises:     036
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "037"
down_revision = "036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── external_event_id ─────────────────────────────────────────────────────
    op.add_column(
        "ingestion_ledger",
        sa.Column("external_event_id", sa.String(500), nullable=True),
    )

    # ── event_version ─────────────────────────────────────────────────────────
    op.add_column(
        "ingestion_ledger",
        sa.Column("event_version", sa.String(10), nullable=True, server_default="1.0"),
    )

    # Back-fill existing rows
    op.execute(
        "UPDATE ingestion_ledger SET event_version = '1.0' WHERE event_version IS NULL"
    )
    # Back-fill manual uploads: external_event_id = "row_{source_row_number}"
    # Only where source_row_number is available
    op.execute(
        """
        UPDATE ingestion_ledger
        SET    external_event_id = 'row_' || source_row_number::text,
               event_version     = '1.1'
        WHERE  source_type = 'manual_upload'
          AND  source_row_number IS NOT NULL
          AND  external_event_id IS NULL
        """
    )

    # ── Partial unique index — idempotency constraint ─────────────────────────
    # Partial: only applies where external_event_id IS NOT NULL.
    # This allows legacy rows (pre-1.1, external_event_id=NULL) to coexist.
    op.create_index(
        "uq_ledger_file_event",
        "ingestion_ledger",
        ["uploaded_file_id", "external_event_id"],
        unique=True,
        postgresql_where=sa.text("external_event_id IS NOT NULL"),
    )

    # ── Regular index for event_version queries ───────────────────────────────
    op.create_index(
        "idx_ingestion_ledger_event_version",
        "ingestion_ledger",
        ["event_version"],
        postgresql_where=sa.text("event_version IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_ingestion_ledger_event_version", table_name="ingestion_ledger")
    op.drop_index("uq_ledger_file_event",               table_name="ingestion_ledger")
    op.drop_column("ingestion_ledger", "event_version")
    op.drop_column("ingestion_ledger", "external_event_id")
