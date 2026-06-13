"""V2: Add full settlement components to settlements_etl and order_financials

Revision ID: 002
Revises: 001
Create Date: 2026-06-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── settlements_etl: add all missing settlement components ─────────────────
    op.add_column("settlements_etl", sa.Column("neft_type", sa.String(50)))
    op.add_column("settlements_etl", sa.Column("sale_amount", sa.Numeric(15, 2)))
    op.add_column("settlements_etl", sa.Column("total_offer_amount", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("my_share", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("customer_addons_amount", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("tcs", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("tds", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("gst_on_mp_fees", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("refund", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("protection_fund", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("fixed_fee", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("collection_fee", sa.Numeric(15, 2), server_default="0"))
    op.add_column("settlements_etl", sa.Column("reverse_shipping_fee", sa.Numeric(15, 2), server_default="0"))

    # ── order_financials: new V2 output columns ────────────────────────────────
    op.add_column("order_financials", sa.Column("sale_amount", sa.Numeric(15, 2)))
    op.add_column("order_financials", sa.Column("total_offer_amount", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("my_share", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("tcs", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("tds", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("gst_on_mp_fees", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("refund", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("invoice_fee_total", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("invoice_gst_total", sa.Numeric(15, 2), server_default="0"))
    op.add_column("order_financials", sa.Column("neft_id", sa.String(200)))
    op.add_column("order_financials", sa.Column("neft_type", sa.String(50)))


def downgrade() -> None:
    for col in ["neft_type", "neft_id", "invoice_gst_total", "invoice_fee_total",
                "refund", "gst_on_mp_fees", "tds", "tcs", "my_share",
                "total_offer_amount", "sale_amount"]:
        op.drop_column("order_financials", col)

    for col in ["reverse_shipping_fee", "collection_fee", "fixed_fee",
                "protection_fund", "refund", "gst_on_mp_fees", "tds", "tcs",
                "customer_addons_amount", "my_share", "total_offer_amount",
                "sale_amount", "neft_type"]:
        op.drop_column("settlements_etl", col)
