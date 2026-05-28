"""Intelligent Report Ingestion Engine — core tables.

Creates:
  uploaded_files           — central file registry (all platforms)
  report_detection_results — auto-detection metadata & confidence scores
  report_schema_versions   — schema catalog
  report_processing_logs   — structured audit trail
  ingestion_ledger         — unified canonical transaction record

Revision ID: 031
Revises: 030
Create Date: 2026-05-28
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "031"
down_revision = "030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── uploaded_files ──────────────────────────────────────────────────────────
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("original_file_name", sa.String(512), nullable=False),
        sa.Column("file_hash_sha256",   sa.String(64),  nullable=False),
        sa.Column("mime_type",          sa.String(100), nullable=True),
        sa.Column("file_size_bytes",    sa.Integer(),   nullable=True),
        sa.Column("upload_source",      sa.String(50),  nullable=False, server_default="web_upload"),
        sa.Column("storage_path",       sa.Text(),      nullable=True),
        sa.Column("upload_status",      sa.String(30),  nullable=False, server_default="uploaded"),
        sa.Column("error_message",      sa.Text(),      nullable=True),
        sa.Column("uploaded_at",        sa.DateTime(),  nullable=False, server_default=sa.text("NOW()")),
        sa.Column("processed_at",       sa.DateTime(),  nullable=True),
    )
    op.create_index("ix_uploaded_files_company_id",       "uploaded_files", ["company_id"])
    op.create_index("ix_uploaded_files_file_hash_sha256", "uploaded_files", ["file_hash_sha256"])
    op.create_index("ix_uploaded_files_upload_status",    "uploaded_files", ["upload_status"])

    # ── report_detection_results ───────────────────────────────────────────────
    op.create_table(
        "report_detection_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("uploaded_files.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("detected_platform",    sa.String(50),     nullable=True),
        sa.Column("detected_report_type", sa.String(50),     nullable=True),
        sa.Column("schema_version",       sa.String(80),     nullable=True),
        sa.Column("confidence_score",     sa.Numeric(5, 4),  nullable=True),
        sa.Column("detection_metadata",   postgresql.JSONB,  nullable=True),
        sa.Column("parser_name",          sa.String(100),    nullable=True),
        sa.Column("needs_manual_review",  sa.Boolean(),      nullable=False, server_default="false"),
        sa.Column("reviewed_by",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at",          sa.DateTime(),     nullable=True),
        sa.Column("created_at",           sa.DateTime(),     nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_report_detection_results_platform",
                    "report_detection_results", ["detected_platform"])

    # ── report_schema_versions ─────────────────────────────────────────────────
    op.create_table(
        "report_schema_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("platform",         sa.String(50),    nullable=False),
        sa.Column("report_type",      sa.String(50),    nullable=False),
        sa.Column("schema_version",   sa.String(80),    nullable=False),
        sa.Column("schema_signature", sa.String(64),    nullable=False),
        sa.Column("expected_columns", postgresql.JSONB, nullable=True),
        sa.Column("optional_columns", postgresql.JSONB, nullable=True),
        sa.Column("parser_name",      sa.String(100),   nullable=True),
        sa.Column("is_active",        sa.Boolean(),     nullable=False, server_default="true"),
        sa.Column("first_seen_at",    sa.DateTime(),    nullable=False, server_default=sa.text("NOW()")),
        sa.Column("created_at",       sa.DateTime(),    nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_report_schema_versions_platform", "report_schema_versions", ["platform"])

    # ── report_processing_logs ─────────────────────────────────────────────────
    op.create_table(
        "report_processing_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level",      sa.String(20), nullable=False),
        sa.Column("stage",      sa.String(50), nullable=False),
        sa.Column("message",    sa.Text(),     nullable=False),
        sa.Column("context",    postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_report_processing_logs_file_id",
                    "report_processing_logs", ["uploaded_file_id"])

    # ── ingestion_ledger ───────────────────────────────────────────────────────
    op.create_table(
        "ingestion_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("uploaded_file_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform",          sa.String(50),      nullable=False),
        sa.Column("report_type",       sa.String(50),      nullable=True),
        sa.Column("order_id",          sa.String(200),     nullable=True),
        sa.Column("shipment_id",       sa.String(200),     nullable=True),
        sa.Column("settlement_id",     sa.String(200),     nullable=True),
        sa.Column("invoice_id",        sa.String(200),     nullable=True),
        sa.Column("sku",               sa.String(200),     nullable=True),
        sa.Column("product_title",     sa.Text(),          nullable=True),
        sa.Column("category",          sa.String(200),     nullable=True),
        sa.Column("transaction_type",  sa.String(50),      nullable=True),
        sa.Column("fee_type",          sa.String(100),     nullable=True),
        sa.Column("amount",            sa.Numeric(18, 2),  nullable=True),
        sa.Column("tax_amount",        sa.Numeric(18, 2),  nullable=True),
        sa.Column("currency",          sa.String(10),      nullable=True, server_default="INR"),
        sa.Column("transaction_date",  sa.String(30),      nullable=True),
        sa.Column("settlement_date",   sa.String(30),      nullable=True),
        sa.Column("return_status",     sa.String(50),      nullable=True),
        sa.Column("payout_status",     sa.String(50),      nullable=True),
        sa.Column("source_row_number", sa.Integer(),       nullable=True),
        sa.Column("lineage_metadata",  postgresql.JSONB,   nullable=True),
        sa.Column("created_at",        sa.DateTime(),      nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_ingestion_ledger_file_id",    "ingestion_ledger", ["uploaded_file_id"])
    op.create_index("ix_ingestion_ledger_company_id", "ingestion_ledger", ["company_id"])
    op.create_index("ix_ingestion_ledger_platform",   "ingestion_ledger", ["platform"])
    op.create_index("ix_ingestion_ledger_order_id",   "ingestion_ledger", ["order_id"])
    op.create_index("ix_ingestion_ledger_sku",        "ingestion_ledger", ["sku"])


def downgrade() -> None:
    op.drop_table("ingestion_ledger")
    op.drop_table("report_processing_logs")
    op.drop_table("report_schema_versions")
    op.drop_table("report_detection_results")
    op.drop_table("uploaded_files")
