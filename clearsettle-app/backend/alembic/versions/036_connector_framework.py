"""
036 — Connector Framework

Adds source provenance fields to ingestion_ledger so every row is traceable
back to the connector that produced it (manual upload, Amazon API, Flipkart API …).

The ETL layer, dashboard, and analytics layers do NOT read these provenance
columns — they are purely for observability and debugging.

Changes:
  ingestion_ledger:
    + source_type   VARCHAR(30)  — manual_upload | amazon_api | flipkart_api | …
    + connection_id UUID FK → marketplace_connections.id  (nullable — manual uploads have none)
    + sync_job_id   UUID FK → marketplace_sync_jobs.id   (nullable — manual uploads have none)

  marketplace_connections (new indexes for common dashboard queries):
    + idx_mc_company_platform  (company_id, marketplace_slug)
    + idx_mc_status            (status)

  report_schema_versions:
    No change — stable.

Revision ID: 036
Revises:     035_add_sku_to_discrepancy_events
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "036"
down_revision = "035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── ingestion_ledger provenance columns ───────────────────────────────────
    op.add_column(
        "ingestion_ledger",
        sa.Column("source_type", sa.String(30), nullable=True),
    )
    op.add_column(
        "ingestion_ledger",
        sa.Column(
            "connection_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("marketplace_connections.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "ingestion_ledger",
        sa.Column(
            "sync_job_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("marketplace_sync_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Back-fill existing rows as manual_upload
    op.execute(
        "UPDATE ingestion_ledger SET source_type = 'manual_upload' WHERE source_type IS NULL"
    )

    # Performance indexes
    op.create_index(
        "idx_ingestion_ledger_source_type",
        "ingestion_ledger",
        ["source_type"],
    )
    op.create_index(
        "idx_ingestion_ledger_connection_id",
        "ingestion_ledger",
        ["connection_id"],
        postgresql_where=sa.text("connection_id IS NOT NULL"),
    )

    # ── marketplace_connections composite index ────────────────────────────────
    # (company_id, marketplace_slug) — used by the dashboard "which platforms
    # are connected" query
    try:
        op.create_index(
            "idx_mc_company_status",
            "marketplace_connections",
            ["company_id", "status"],
        )
    except Exception:
        pass  # index may already exist from 032

    # ── uploaded_files: add source_type for quick filter ─────────────────────
    # Optional enhancement: mirrors ingestion_ledger for join-free queries
    try:
        op.add_column(
            "uploaded_files",
            sa.Column("source_type", sa.String(30), nullable=True, server_default="manual_upload"),
        )
        op.execute(
            "UPDATE uploaded_files SET source_type = 'manual_upload' WHERE source_type IS NULL"
        )
    except Exception:
        pass  # column may already exist if re-running migration


def downgrade() -> None:
    op.drop_index("idx_ingestion_ledger_connection_id", table_name="ingestion_ledger")
    op.drop_index("idx_ingestion_ledger_source_type", table_name="ingestion_ledger")
    op.drop_column("ingestion_ledger", "sync_job_id")
    op.drop_column("ingestion_ledger", "connection_id")
    op.drop_column("ingestion_ledger", "source_type")
    try:
        op.drop_column("uploaded_files", "source_type")
    except Exception:
        pass
