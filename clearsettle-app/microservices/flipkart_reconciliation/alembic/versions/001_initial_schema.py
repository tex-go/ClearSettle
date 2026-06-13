"""Initial schema: raw, etl, and business layers

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Raw Layer ──────────────────────────────────────────────────────────────
    for table in ("orders_raw", "fees_raw", "settlements_raw"):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("file_name", sa.String(500), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        )
        op.create_index(f"ix_{table}_batch_id", table, ["batch_id"])

    # ── ETL Layer — Orders ─────────────────────────────────────────────────────
    op.create_table(
        "orders_etl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.String(100), nullable=False),
        sa.Column("order_id", sa.String(100)),
        sa.Column("sku", sa.String(200)),
        sa.Column("fsn", sa.String(200)),
        sa.Column("product_title", sa.String(1000)),
        sa.Column("quantity", sa.Integer()),
        sa.Column("order_date", sa.Date()),
        sa.Column("dispatch_date", sa.Date()),
        sa.Column("delivery_date", sa.Date()),
        sa.Column("order_item_status", sa.String(100)),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("validation_errors", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_orders_etl_batch_id", "orders_etl", ["batch_id"])
    op.create_index("ix_orders_etl_order_item_id", "orders_etl", ["order_item_id"])

    # ── ETL Layer — Fees ───────────────────────────────────────────────────────
    op.create_table(
        "fees_etl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", sa.Integer(), nullable=False),
        sa.Column("order_item_id", sa.String(100), nullable=False),
        sa.Column("fee_name", sa.String(200)),
        sa.Column("fee_amount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("fee_waiver_amount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("cgst", sa.Numeric(15, 2), server_default="0"),
        sa.Column("sgst", sa.Numeric(15, 2), server_default="0"),
        sa.Column("igst", sa.Numeric(15, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("fee_date", sa.Date()),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("validation_errors", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fees_etl_batch_id", "fees_etl", ["batch_id"])
    op.create_index("ix_fees_etl_order_item_id", "fees_etl", ["order_item_id"])

    # ── ETL Layer — Settlements ────────────────────────────────────────────────
    op.create_table(
        "settlements_etl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_id", sa.Integer(), nullable=False),
        sa.Column("neft_id", sa.String(200)),
        sa.Column("settlement_date", sa.Date()),
        sa.Column("settlement_amount", sa.Numeric(15, 2)),
        sa.Column("order_id", sa.String(100)),
        sa.Column("order_item_id", sa.String(100), nullable=False),
        sa.Column("selling_price", sa.Numeric(15, 2)),
        sa.Column("marketplace_fee", sa.Numeric(15, 2), server_default="0"),
        sa.Column("taxes", sa.Numeric(15, 2), server_default="0"),
        sa.Column("offer_adjustments", sa.Numeric(15, 2), server_default="0"),
        sa.Column("shipping_charges", sa.Numeric(15, 2), server_default="0"),
        sa.Column("sku", sa.String(200)),
        sa.Column("fsn", sa.String(200)),
        sa.Column("is_valid", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("validation_errors", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_settlements_etl_batch_id", "settlements_etl", ["batch_id"])
    op.create_index("ix_settlements_etl_order_item_id", "settlements_etl", ["order_item_id"])

    # ── Business Layer ─────────────────────────────────────────────────────────
    op.create_table(
        "order_financials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_item_id", sa.String(100), nullable=False, unique=True),
        sa.Column("order_id", sa.String(100)),
        sa.Column("sku", sa.String(200)),
        sa.Column("fsn", sa.String(200)),
        sa.Column("product_title", sa.String(1000)),
        sa.Column("order_date", sa.Date()),
        sa.Column("delivery_date", sa.Date()),
        sa.Column("selling_price", sa.Numeric(15, 2)),
        sa.Column("marketplace_fee", sa.Numeric(15, 2), server_default="0"),
        sa.Column("commission_fee", sa.Numeric(15, 2), server_default="0"),
        sa.Column("shipping_fee", sa.Numeric(15, 2), server_default="0"),
        sa.Column("tax_amount", sa.Numeric(15, 2), server_default="0"),
        sa.Column("other_fee", sa.Numeric(15, 2), server_default="0"),
        sa.Column("settlement_amount", sa.Numeric(15, 2)),
        sa.Column("settlement_date", sa.Date()),
        sa.Column("expected_settlement", sa.Numeric(15, 2)),
        sa.Column("difference", sa.Numeric(15, 2)),
        sa.Column("reconciliation_status", sa.String(50), nullable=False),
        sa.Column("last_reconciled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_order_financials_order_item_id", "order_financials", ["order_item_id"], unique=True)
    op.create_index("ix_order_financials_order_id", "order_financials", ["order_id"])
    op.create_index("ix_order_financials_status", "order_financials", ["reconciliation_status"])


def downgrade() -> None:
    op.drop_table("order_financials")
    op.drop_table("settlements_etl")
    op.drop_table("fees_etl")
    op.drop_table("orders_etl")
    for table in ("orders_raw", "fees_raw", "settlements_raw"):
        op.drop_table(table)
