"""Settlement ingestion tables

New tables
----------
settlements
  One row per marketplace settlement period.
  UNIQUE (company_id, platform, external_id) — prevents duplicate ingestion.

settlement_transactions
  One row per financial event (shipment, refund, service_fee, adjustment, …).
  UNIQUE (source_hash) — SHA-256 dedup key computed from platform-native fields.
  Composite index on (settlement_id, order_id) for order lookups.

fees
  One fee line-item per settlement transaction.
  Indexed on (settlement_id) for fast settlement → fees queries.
  Indexed on (transaction_id) for fast transaction → fees queries.

payout_events
  One fund-transfer record per closed settlement.
  UNIQUE (settlement_id) — one payout per settlement.

Revision ID: 006
Revises: 005
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── settlements ──────────────────────────────────────────────────────────
    op.create_table(
        "settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_connections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("platform",    sa.String(50),  nullable=False, server_default="amazon"),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("status",      sa.String(50),  nullable=False, server_default="processing"),
        sa.Column("currency",    sa.String(10),  nullable=False, server_default="INR"),

        # Financial summary
        sa.Column("total_amount",         sa.Numeric(15, 4), nullable=False, server_default="0"),
        sa.Column("converted_amount",     sa.Numeric(15, 4)),
        sa.Column("fund_transfer_amount", sa.Numeric(15, 4)),
        sa.Column("beginning_balance",    sa.Numeric(15, 4)),
        sa.Column("transactions_count",   sa.Integer(), server_default="0"),
        sa.Column("fees_total",           sa.Numeric(15, 4), server_default="0"),

        # Period
        sa.Column("period_start",       sa.DateTime()),
        sa.Column("period_end",         sa.DateTime()),
        sa.Column("fund_transfer_date", sa.DateTime()),
        sa.Column("account_tail",       sa.String(10)),

        # Raw data
        sa.Column("raw_data_json", sa.Text()),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),

        sa.UniqueConstraint("company_id", "platform", "external_id",
                            name="uq_settlement_company_platform_ext"),
    )
    op.create_index("ix_settlements_company_id", "settlements", ["company_id"])
    op.create_index("ix_settlements_platform",   "settlements", ["platform"])
    op.create_index("ix_settlements_status",     "settlements", ["status"])

    # ── settlement_transactions ──────────────────────────────────────────────
    op.create_table(
        "settlement_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="amazon"),

        # Dedup
        sa.Column("source_hash", sa.String(64), nullable=False),

        # Classification
        sa.Column("transaction_type", sa.String(50),  nullable=False),
        sa.Column("order_id",         sa.String(50)),
        sa.Column("order_item_id",    sa.String(255)),
        sa.Column("sku",              sa.String(255)),
        sa.Column("marketplace",      sa.String(100)),
        sa.Column("posted_date",      sa.DateTime()),
        sa.Column("quantity",         sa.Integer(), server_default="1"),

        # Amounts
        sa.Column("currency",         sa.String(10),     nullable=False, server_default="INR"),
        sa.Column("principal_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("shipping_amount",  sa.Numeric(15, 4), server_default="0"),
        sa.Column("gift_wrap_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("promotion_amount", sa.Numeric(15, 4), server_default="0"),
        sa.Column("total_amount",     sa.Numeric(15, 4), server_default="0"),
        sa.Column("fees_total",       sa.Numeric(15, 4), server_default="0"),
        sa.Column("net_amount",       sa.Numeric(15, 4), server_default="0"),

        # Raw data
        sa.Column("raw_data_json", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),

        sa.UniqueConstraint("source_hash", name="uq_stxn_source_hash"),
    )
    op.create_index("ix_stxn_settlement_id",      "settlement_transactions", ["settlement_id"])
    op.create_index("ix_stxn_company_id",         "settlement_transactions", ["company_id"])
    op.create_index("ix_stxn_transaction_type",   "settlement_transactions", ["transaction_type"])
    op.create_index("ix_stxn_order_id",           "settlement_transactions", ["order_id"])
    op.create_index("ix_stxn_posted_date",        "settlement_transactions", ["posted_date"])
    op.create_index("ix_stxn_settlement_order",   "settlement_transactions", ["settlement_id", "order_id"])

    # ── fees ─────────────────────────────────────────────────────────────────
    op.create_table(
        "fees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlement_transactions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="amazon"),

        sa.Column("fee_type",        sa.String(100), nullable=False),
        sa.Column("fee_description", sa.String(255)),
        sa.Column("currency",        sa.String(10),     nullable=False, server_default="INR"),
        sa.Column("amount",          sa.Numeric(15, 4), nullable=False),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_fees_transaction_id", "fees", ["transaction_id"])
    op.create_index("ix_fees_settlement_id",  "fees", ["settlement_id"])
    op.create_index("ix_fees_company_id",     "fees", ["company_id"])
    op.create_index("ix_fees_fee_type",       "fees", ["fee_type"])

    # ── payout_events ─────────────────────────────────────────────────────────
    op.create_table(
        "payout_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_connections.id", ondelete="SET NULL"), nullable=True),

        sa.Column("platform",     sa.String(50),  nullable=False, server_default="amazon"),
        sa.Column("external_id",  sa.String(255)),
        sa.Column("status",       sa.String(50),  nullable=False, server_default="pending"),
        sa.Column("currency",     sa.String(10),  nullable=False, server_default="INR"),
        sa.Column("amount",       sa.Numeric(15, 4), nullable=False),
        sa.Column("transfer_date", sa.DateTime()),
        sa.Column("account_tail", sa.String(10)),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),

        sa.UniqueConstraint("settlement_id", name="uq_payout_settlement"),
    )
    op.create_index("ix_payout_settlement_id", "payout_events", ["settlement_id"])
    op.create_index("ix_payout_company_id",    "payout_events", ["company_id"])
    op.create_index("ix_payout_status",        "payout_events", ["status"])


def downgrade() -> None:
    op.drop_table("payout_events")
    op.drop_table("fees")
    op.drop_table("settlement_transactions")
    op.drop_table("settlements")
