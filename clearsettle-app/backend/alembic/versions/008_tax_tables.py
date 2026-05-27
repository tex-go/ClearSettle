"""GST/TCS engine tables

New tables
----------
tax_ledger_entries
  One row per tax line-item extracted from a settlement transaction or fee.
  entry_type: tcs_deducted | gst_on_fee | gst_on_sale | gst_on_refund

  India context:
    - tcs_deducted: TCS withheld by e-commerce operator (Section 52 CGST Act, 1%)
    - gst_on_fee:   18% IGST on marketplace fees — ITC claimable by the seller
    - gst_on_sale:  GST on shipment transactions (informational; rate by HSN)
    - gst_on_refund: GST reversal on returned orders

  Idempotency: all entries for a settlement are deleted and reinserted on
  re-processing, so re-runs produce a clean, consistent ledger.

monthly_tax_summaries
  One row per (company_id, platform, period) — aggregated from ledger entries.
  Rebuilt on demand; UNIQUE constraint prevents duplicates.
  is_finalized=True locks the row against automatic recomputation (GSTR-2A filed).

Revision ID: 008
Revises: 007
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── tax_ledger_entries ────────────────────────────────────────────────────
    op.create_table(
        "tax_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform",   sa.String(50), nullable=False, server_default="amazon"),
        sa.Column("period",     sa.String(7),  nullable=False),   # YYYY-MM
        sa.Column("entry_type", sa.String(50), nullable=False),

        # Source linkage
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlement_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("fee_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("fees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id",  sa.String(50)),
        sa.Column("fee_type",  sa.String(100)),

        # Tax computation
        sa.Column("taxable_amount", sa.Numeric(15, 4), nullable=False, server_default="0"),
        sa.Column("tax_rate_pct",   sa.Numeric(6,  4), nullable=False, server_default="0"),
        sa.Column("tax_amount",     sa.Numeric(15, 4), nullable=False, server_default="0"),

        # GST component breakdown
        sa.Column("igst_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("cgst_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("sgst_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("cess_amount", sa.Numeric(15, 4), server_default="0"),

        # Classification
        sa.Column("supply_type", sa.String(20), server_default="inter_state"),
        sa.Column("is_reversal", sa.Boolean,    nullable=False, server_default="false"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_index("ix_tle_company_id",     "tax_ledger_entries", ["company_id"])
    op.create_index("ix_tle_settlement_id",  "tax_ledger_entries", ["settlement_id"])
    op.create_index("ix_tle_period",         "tax_ledger_entries", ["period"])
    op.create_index("ix_tle_entry_type",     "tax_ledger_entries", ["entry_type"])
    op.create_index("ix_tle_company_period", "tax_ledger_entries", ["company_id", "period"])

    # ── monthly_tax_summaries ─────────────────────────────────────────────────
    op.create_table(
        "monthly_tax_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="amazon"),
        sa.Column("period",   sa.String(7),  nullable=False),   # YYYY-MM

        # Sales
        sa.Column("gross_sales",   sa.Numeric(15, 4), server_default="0"),
        sa.Column("refund_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("net_sales",     sa.Numeric(15, 4), server_default="0"),

        # TCS (deducted by marketplace)
        sa.Column("tcs_deducted", sa.Numeric(15, 4), server_default="0"),
        sa.Column("tcs_igst",     sa.Numeric(15, 4), server_default="0"),
        sa.Column("tcs_cgst",     sa.Numeric(15, 4), server_default="0"),
        sa.Column("tcs_sgst",     sa.Numeric(15, 4), server_default="0"),

        # GST on marketplace fees (ITC)
        sa.Column("total_fees",   sa.Numeric(15, 4), server_default="0"),
        sa.Column("gst_on_fees",  sa.Numeric(15, 4), server_default="0"),
        sa.Column("igst_on_fees", sa.Numeric(15, 4), server_default="0"),
        sa.Column("cgst_on_fees", sa.Numeric(15, 4), server_default="0"),
        sa.Column("sgst_on_fees", sa.Numeric(15, 4), server_default="0"),

        # Refund GST
        sa.Column("gst_on_refunds", sa.Numeric(15, 4), server_default="0"),

        # Metadata
        sa.Column("settlements_processed", sa.Integer, server_default="0"),
        sa.Column("transactions_count",    sa.Integer, server_default="0"),
        sa.Column("fees_count",            sa.Integer, server_default="0"),

        # Derived
        sa.Column("net_tcs_credit", sa.Numeric(15, 4), server_default="0"),
        sa.Column("itc_claimable",  sa.Numeric(15, 4), server_default="0"),

        # Lifecycle
        sa.Column("is_finalized", sa.Boolean,  nullable=False, server_default="false"),
        sa.Column("finalized_at", sa.DateTime, nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),

        sa.UniqueConstraint("company_id", "platform", "period",
                            name="uq_mts_company_platform_period"),
    )

    op.create_index("ix_mts_company_id", "monthly_tax_summaries", ["company_id"])
    op.create_index("ix_mts_period",     "monthly_tax_summaries", ["period"])


def downgrade() -> None:
    op.drop_table("monthly_tax_summaries")
    op.drop_table("tax_ledger_entries")
