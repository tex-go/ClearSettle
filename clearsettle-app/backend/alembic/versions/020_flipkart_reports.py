"""Flipkart P&L Report ingestion tables.

Revision ID: 020
Revises: 019
Create Date: 2026-05-22

Creates:
  flipkart_reports      — uploaded report metadata + processing status
  flipkart_summaries    — overall summary KPIs (one per report)
  flipkart_sku_pl       — per-SKU P&L rows
  flipkart_orders_pl    — per-order P&L rows with settlement tracking
  flipkart_recon_issues — detected settlement reconciliation issues
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── flipkart_reports ──────────────────────────────────────────────────────
    op.create_table(
        "flipkart_reports",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename",         sa.String(255), nullable=False),
        sa.Column("original_name",    sa.String(255), nullable=False),
        sa.Column("file_size_bytes",  sa.Integer,     nullable=True),
        sa.Column("status",           sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("error_message",    sa.Text,        nullable=True),
        sa.Column("report_period",    sa.String(100), nullable=True),
        sa.Column("sheets_parsed",    sa.String(500), nullable=True),
        sa.Column("row_count_summary",sa.Integer,     nullable=True),
        sa.Column("row_count_sku",    sa.Integer,     nullable=True),
        sa.Column("row_count_orders", sa.Integer,     nullable=True),
        sa.Column("uploaded_at",      sa.DateTime,    nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at",     sa.DateTime,    nullable=True),
    )
    op.create_index("ix_flipkart_reports_company_id", "flipkart_reports", ["company_id"])

    # ── flipkart_summaries ────────────────────────────────────────────────────
    op.create_table(
        "flipkart_summaries",
        sa.Column("id",                     postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",              postgresql.UUID(as_uuid=True), sa.ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        # Revenue
        sa.Column("gross_sales",            sa.Numeric(18, 2), nullable=True),
        sa.Column("returns",                sa.Numeric(18, 2), nullable=True),
        sa.Column("cancellations",          sa.Numeric(18, 2), nullable=True),
        sa.Column("net_sales",              sa.Numeric(18, 2), nullable=True),
        # Fees
        sa.Column("commission",             sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_charges",       sa.Numeric(18, 2), nullable=True),
        sa.Column("reverse_shipping",       sa.Numeric(18, 2), nullable=True),
        sa.Column("collection_fees",        sa.Numeric(18, 2), nullable=True),
        sa.Column("fixed_fees",             sa.Numeric(18, 2), nullable=True),
        sa.Column("gst_on_fees",            sa.Numeric(18, 2), nullable=True),
        sa.Column("tcs",                    sa.Numeric(18, 2), nullable=True),
        sa.Column("tds",                    sa.Numeric(18, 2), nullable=True),
        sa.Column("other_fees",             sa.Numeric(18, 2), nullable=True),
        sa.Column("total_fees",             sa.Numeric(18, 2), nullable=True),
        # Earnings
        sa.Column("net_earnings",           sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_settled",         sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_pending",         sa.Numeric(18, 2), nullable=True),
        # Volumes
        sa.Column("total_orders",           sa.Integer,        nullable=True),
        sa.Column("total_returned_orders",  sa.Integer,        nullable=True),
        sa.Column("total_cancelled_orders", sa.Integer,        nullable=True),
        # Rate KPIs
        sa.Column("return_rate_pct",        sa.Numeric(6, 3),  nullable=True),
        sa.Column("cancellation_rate_pct",  sa.Numeric(6, 3),  nullable=True),
        sa.Column("profit_margin_pct",      sa.Numeric(8, 4),  nullable=True),
    )
    op.create_index("ix_flipkart_summaries_company_id", "flipkart_summaries", ["company_id"])

    # ── flipkart_sku_pl ───────────────────────────────────────────────────────
    op.create_table(
        "flipkart_sku_pl",
        sa.Column("id",                    postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",             postgresql.UUID(as_uuid=True), sa.ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",            postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_code",              sa.String(200), nullable=True),
        sa.Column("product_title",         sa.String(500), nullable=True),
        sa.Column("category",              sa.String(200), nullable=True),
        sa.Column("selling_price",         sa.Numeric(14, 2), nullable=True),
        sa.Column("mrp",                   sa.Numeric(14, 2), nullable=True),
        sa.Column("total_orders",          sa.Integer,        nullable=True),
        sa.Column("qty_sold",              sa.Numeric(12, 3), nullable=True),
        sa.Column("gross_sales",           sa.Numeric(18, 2), nullable=True),
        sa.Column("returns_qty",           sa.Numeric(12, 3), nullable=True),
        sa.Column("returns_value",         sa.Numeric(18, 2), nullable=True),
        sa.Column("cancellations_qty",     sa.Numeric(12, 3), nullable=True),
        sa.Column("cancellations_value",   sa.Numeric(18, 2), nullable=True),
        sa.Column("net_sales",             sa.Numeric(18, 2), nullable=True),
        sa.Column("commission",            sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_charges",      sa.Numeric(18, 2), nullable=True),
        sa.Column("reverse_shipping",      sa.Numeric(18, 2), nullable=True),
        sa.Column("other_fees",            sa.Numeric(18, 2), nullable=True),
        sa.Column("total_fees",            sa.Numeric(18, 2), nullable=True),
        sa.Column("net_earnings",          sa.Numeric(18, 2), nullable=True),
        sa.Column("margin_pct",            sa.Numeric(8, 4),  nullable=True),
        sa.Column("return_rate_pct",       sa.Numeric(6, 3),  nullable=True),
        sa.Column("cancellation_rate_pct", sa.Numeric(6, 3),  nullable=True),
        sa.Column("is_loss_making",        sa.Boolean,        nullable=False, server_default="false"),
        sa.Column("high_return_rate",      sa.Boolean,        nullable=False, server_default="false"),
    )
    op.create_index("ix_flipkart_sku_pl_report_id",  "flipkart_sku_pl", ["report_id"])
    op.create_index("ix_flipkart_sku_pl_company_id", "flipkart_sku_pl", ["company_id"])
    op.create_index("ix_flipkart_sku_pl_sku_code",   "flipkart_sku_pl", ["sku_code"])

    # ── flipkart_orders_pl ────────────────────────────────────────────────────
    op.create_table(
        "flipkart_orders_pl",
        sa.Column("id",                  postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",           postgresql.UUID(as_uuid=True), sa.ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id",            sa.String(100), nullable=True),
        sa.Column("order_date",          sa.Date,        nullable=True),
        sa.Column("sku_code",            sa.String(200), nullable=True),
        sa.Column("product_title",       sa.String(500), nullable=True),
        sa.Column("category",            sa.String(200), nullable=True),
        sa.Column("selling_price",       sa.Numeric(14, 2), nullable=True),
        sa.Column("quantity",            sa.Numeric(12, 3), nullable=True),
        sa.Column("gross_amount",        sa.Numeric(18, 2), nullable=True),
        sa.Column("commission",          sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_charges",    sa.Numeric(18, 2), nullable=True),
        sa.Column("reverse_shipping",    sa.Numeric(18, 2), nullable=True),
        sa.Column("other_fees",          sa.Numeric(18, 2), nullable=True),
        sa.Column("net_earnings",        sa.Numeric(18, 2), nullable=True),
        sa.Column("status",              sa.String(50),  nullable=True),
        sa.Column("settlement_status",   sa.String(50),  nullable=True),
        sa.Column("settlement_amount",   sa.Numeric(18, 2), nullable=True),
        sa.Column("settlement_date",     sa.Date,           nullable=True),
        sa.Column("expected_settlement", sa.Numeric(18, 2), nullable=True),
        sa.Column("settlement_variance", sa.Numeric(18, 2), nullable=True),
    )
    op.create_index("ix_flipkart_orders_pl_report_id",  "flipkart_orders_pl", ["report_id"])
    op.create_index("ix_flipkart_orders_pl_company_id", "flipkart_orders_pl", ["company_id"])
    op.create_index("ix_flipkart_orders_pl_order_id",   "flipkart_orders_pl", ["order_id"])
    op.create_index("ix_flipkart_orders_pl_sku_code",   "flipkart_orders_pl", ["sku_code"])

    # ── flipkart_recon_issues ─────────────────────────────────────────────────
    op.create_table(
        "flipkart_recon_issues",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("flipkart_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issue_type",      sa.String(50),  nullable=False),
        sa.Column("severity",        sa.String(20),  nullable=False),
        sa.Column("order_id",        sa.String(100), nullable=True),
        sa.Column("sku_code",        sa.String(200), nullable=True),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_amount",   sa.Numeric(18, 2), nullable=True),
        sa.Column("variance",        sa.Numeric(18, 2), nullable=True),
        sa.Column("description",     sa.Text,        nullable=False),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="open"),
        sa.Column("created_at",      sa.DateTime,    nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_flipkart_recon_issues_report_id",  "flipkart_recon_issues", ["report_id"])
    op.create_index("ix_flipkart_recon_issues_company_id", "flipkart_recon_issues", ["company_id"])
    op.create_index("ix_flipkart_recon_issues_issue_type", "flipkart_recon_issues", ["issue_type"])


def downgrade() -> None:
    op.drop_table("flipkart_recon_issues")
    op.drop_table("flipkart_orders_pl")
    op.drop_table("flipkart_sku_pl")
    op.drop_table("flipkart_summaries")
    op.drop_table("flipkart_reports")
