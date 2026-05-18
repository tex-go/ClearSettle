"""Phase 2A — Provenance metadata + reconciliation rule classification

PURPOSE
-------
Two structural gaps are fixed here as preparation for the canonical
reconciliation architecture:

1. PROVENANCE FIELDS (6 tables)
   Every row ingested into the reconciliation pipeline must carry metadata
   that answers: where did this data come from, and how confident are we in it?

   Fields added to: recon_files, stg_settlement_lines, stg_invoice_lines,
                    stg_chargeback_lines, stg_payment_lines, stg_operational_lines

   source_type            — origin category: file_upload | api | manual
   ingestion_method       — exact method:    csv_upload | xlsx_upload |
                                             amazon_sp_api | flipkart_api | ...
   document_origin        — human-readable source: "amazon.in" | "flipkart.com"
                            | uploaded filename
   source_confidence_score — 0.000–1.000; api=1.0, csv=0.9, xlsx=0.85, manual=0.7

   All columns are nullable with no server_default so existing rows are
   unaffected and the migration is fully backward-compatible.

2. RULE CLASSIFICATION (reconciliation_rules)
   The reconciliation_rules table was built for the OLD settlement engine.
   The NEW vendor engine hardcodes its thresholds in Python. Phase 2C will
   make the NEW engine load from this table. In preparation:

   system_type    — which engine owns this rule: settlement | vendor | both
   detector_name  — exact Python function name: detect_duplicate_deductions, ...

   Existing 7 rules are updated to system_type='settlement'.
   An index on system_type is added so the engine can efficiently load only
   rules relevant to a given run context.

NO DESTRUCTIVE CHANGES. All new columns are nullable. Existing rows are
untouched except for the UPDATE that back-fills system_type on the 7
pre-existing global rules.

Revision ID: 014
Revises: 013
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Provenance columns shared across all staging tables ───────────────────────
# Defined once and applied to each table to avoid repetition.
_PROVENANCE_COLS = [
    sa.Column("source_type",             sa.String(30),      nullable=True),
    sa.Column("ingestion_method",        sa.String(100),     nullable=True),
    sa.Column("document_origin",         sa.String(150),     nullable=True),
    sa.Column("source_confidence_score", sa.Numeric(4, 3),   nullable=True),
]

_STAGING_TABLES = [
    "stg_settlement_lines",
    "stg_invoice_lines",
    "stg_chargeback_lines",
    "stg_payment_lines",
    "stg_operational_lines",
]


def upgrade() -> None:
    # ── 1. recon_files — provenance ───────────────────────────────────────────
    # recon_files tracks uploaded or API-fetched source files.
    # source_type here describes how the file itself arrived (file_upload vs api).
    op.add_column("recon_files", sa.Column("source_type",             sa.String(30),    nullable=True))
    op.add_column("recon_files", sa.Column("ingestion_method",        sa.String(100),   nullable=True))
    op.add_column("recon_files", sa.Column("document_origin",         sa.String(150),   nullable=True))
    op.add_column("recon_files", sa.Column("source_confidence_score", sa.Numeric(4, 3), nullable=True))

    # ── 2. All staging tables — provenance ────────────────────────────────────
    # Each parsed row inherits provenance from its source file (or API call).
    # Stored on the row itself for query efficiency — no join to recon_files needed.
    for table in _STAGING_TABLES:
        op.add_column(table, sa.Column("source_type",             sa.String(30),    nullable=True))
        op.add_column(table, sa.Column("ingestion_method",        sa.String(100),   nullable=True))
        op.add_column(table, sa.Column("document_origin",         sa.String(150),   nullable=True))
        op.add_column(table, sa.Column("source_confidence_score", sa.Numeric(4, 3), nullable=True))

    # ── 3. reconciliation_rules — classification columns ─────────────────────
    op.add_column(
        "reconciliation_rules",
        sa.Column("system_type",   sa.String(20),  nullable=True),
        # settlement | vendor | both
        # Nullable now; back-filled immediately below for existing rows.
        # Future inserts must supply this field.
    )
    op.add_column(
        "reconciliation_rules",
        sa.Column("detector_name", sa.String(100), nullable=True),
        # Canonical Python function name in the detector module.
        # Allows the engine to resolve detectors dynamically without code changes.
    )
    op.create_index(
        "ix_recon_rules_system_type",
        "reconciliation_rules",
        ["system_type"],
    )

    # ── 4. Back-fill system_type for the 7 pre-existing global rules ──────────
    # These were created in migration 007 for the OLD settlement engine.
    # rule_type is the stable identifier; detector_name is the Python function.
    # One UPDATE per rule — each op.execute() must be a single statement.

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_missing_payout'
        WHERE rule_type = 'missing_payout'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_payout_mismatch'
        WHERE rule_type = 'payout_amount_mismatch'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_referral_fee_overcharge'
        WHERE rule_type = 'referral_fee_overcharge'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_fba_fee_overcharge'
        WHERE rule_type = 'fba_fee_overcharge'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_duplicate_deductions'
        WHERE rule_type = 'duplicate_deduction'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_unexpected_fees'
        WHERE rule_type = 'unexpected_fee'
          AND company_id IS NULL
    """)

    op.execute("""
        UPDATE reconciliation_rules
        SET system_type = 'settlement',
            detector_name = 'detect_penalty_mismatches'
        WHERE rule_type = 'penalty_mismatch'
          AND company_id IS NULL
    """)


def downgrade() -> None:
    # Remove rule classification index + columns
    op.drop_index("ix_recon_rules_system_type", table_name="reconciliation_rules")
    op.drop_column("reconciliation_rules", "detector_name")
    op.drop_column("reconciliation_rules", "system_type")

    # Remove provenance columns from all staging tables
    for table in reversed(_STAGING_TABLES):
        op.drop_column(table, "source_confidence_score")
        op.drop_column(table, "document_origin")
        op.drop_column(table, "ingestion_method")
        op.drop_column(table, "source_type")

    # Remove provenance columns from recon_files
    op.drop_column("recon_files", "source_confidence_score")
    op.drop_column("recon_files", "document_origin")
    op.drop_column("recon_files", "ingestion_method")
    op.drop_column("recon_files", "source_type")
