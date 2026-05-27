"""Amazon settlement report tables.

Revision ID: 026
Revises: 025
Create Date: 2026-05-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "amazon_reports",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename",         sa.String(255), nullable=False),
        sa.Column("original_name",    sa.String(255), nullable=False),
        sa.Column("file_size_bytes",  sa.Integer,     nullable=True),
        sa.Column("file_hash",        sa.String(64),  nullable=True),
        sa.Column("report_type",      sa.String(30),  nullable=False, server_default="settlement_report"),
        sa.Column("status",           sa.String(50),  nullable=False, server_default="pending"),
        sa.Column("error_message",    sa.Text,        nullable=True),
        sa.Column("settlement_id",        sa.String(100),     nullable=True),
        sa.Column("settlement_start_date",sa.Date,            nullable=True),
        sa.Column("settlement_end_date",  sa.Date,            nullable=True),
        sa.Column("deposit_date",         sa.Date,            nullable=True),
        sa.Column("currency",             sa.String(10),      nullable=True),
        sa.Column("total_deposit_amount", sa.Numeric(18, 2),  nullable=True),
        sa.Column("row_count",        sa.Integer,     nullable=True),
        sa.Column("uploaded_at",      sa.DateTime,    nullable=False),
        sa.Column("processed_at",     sa.DateTime,    nullable=True),
    )
    op.create_index("ix_amazon_reports_company_id", "amazon_reports", ["company_id"])
    op.create_index("ix_amazon_reports_file_hash",  "amazon_reports", ["file_hash"])

    op.create_table(
        "amazon_summaries",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gross_sales",          sa.Numeric(18, 2), nullable=True),
        sa.Column("refunds",              sa.Numeric(18, 2), nullable=True),
        sa.Column("promotions",           sa.Numeric(18, 2), nullable=True),
        sa.Column("net_sales",            sa.Numeric(18, 2), nullable=True),
        sa.Column("commission",           sa.Numeric(18, 2), nullable=True),
        sa.Column("fba_fees",             sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_fees",        sa.Numeric(18, 2), nullable=True),
        sa.Column("other_fees",           sa.Numeric(18, 2), nullable=True),
        sa.Column("withheld_tax",         sa.Numeric(18, 2), nullable=True),
        sa.Column("total_fees",           sa.Numeric(18, 2), nullable=True),
        sa.Column("net_earnings",         sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_deposited",     sa.Numeric(18, 2), nullable=True),
        sa.Column("settlement_variance",  sa.Numeric(18, 2), nullable=True),
        sa.Column("total_orders",         sa.Integer, nullable=True),
        sa.Column("total_refunded_orders",sa.Integer, nullable=True),
        sa.Column("total_units",          sa.Integer, nullable=True),
        sa.Column("effective_commission_rate_pct", sa.Numeric(6, 3), nullable=True),
        sa.Column("return_rate_pct",               sa.Numeric(6, 3), nullable=True),
        sa.Column("fee_rate_pct",                  sa.Numeric(6, 3), nullable=True),
    )
    op.create_index("ix_amazon_summaries_company_id", "amazon_summaries", ["company_id"])

    op.create_table(
        "amazon_order_rows",
        sa.Column("id",                 postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",          postgresql.UUID(as_uuid=True), sa.ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",         postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id",           sa.String(100), nullable=True),
        sa.Column("merchant_order_id",  sa.String(100), nullable=True),
        sa.Column("order_date",         sa.Date,        nullable=True),
        sa.Column("shipment_date",      sa.Date,        nullable=True),
        sa.Column("posted_date",        sa.Date,        nullable=True),
        sa.Column("sku",                sa.String(200), nullable=True),
        sa.Column("product_name",       sa.String(500), nullable=True),
        sa.Column("quantity",           sa.Integer,     nullable=True),
        sa.Column("transaction_type",   sa.String(50),  nullable=True),
        sa.Column("gross_amount",       sa.Numeric(18, 2), nullable=True),
        sa.Column("commission",         sa.Numeric(18, 2), nullable=True),
        sa.Column("fba_fee",            sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_fee",       sa.Numeric(18, 2), nullable=True),
        sa.Column("other_fees",         sa.Numeric(18, 2), nullable=True),
        sa.Column("withheld_tax",       sa.Numeric(18, 2), nullable=True),
        sa.Column("promotions",         sa.Numeric(18, 2), nullable=True),
        sa.Column("net_amount",         sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_net",       sa.Numeric(18, 2), nullable=True),
        sa.Column("settlement_variance",sa.Numeric(18, 2), nullable=True),
    )
    op.create_index("ix_amazon_order_rows_report_id",  "amazon_order_rows", ["report_id"])
    op.create_index("ix_amazon_order_rows_company_id", "amazon_order_rows", ["company_id"])
    op.create_index("ix_amazon_order_rows_order_id",   "amazon_order_rows", ["order_id"])
    op.create_index("ix_amazon_order_rows_sku",        "amazon_order_rows", ["sku"])

    op.create_table(
        "amazon_recon_issues",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("amazon_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issue_type",      sa.String(60),  nullable=False),
        sa.Column("severity",        sa.String(20),  nullable=False),
        sa.Column("order_id",        sa.String(100), nullable=True),
        sa.Column("sku",             sa.String(200), nullable=True),
        sa.Column("expected_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("actual_amount",   sa.Numeric(18, 2), nullable=True),
        sa.Column("variance",        sa.Numeric(18, 2), nullable=True),
        sa.Column("description",     sa.Text,        nullable=False),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="open"),
        sa.Column("created_at",      sa.DateTime,    nullable=False),
    )
    op.create_index("ix_amazon_recon_issues_report_id",   "amazon_recon_issues", ["report_id"])
    op.create_index("ix_amazon_recon_issues_company_id",  "amazon_recon_issues", ["company_id"])
    op.create_index("ix_amazon_recon_issues_issue_type",  "amazon_recon_issues", ["issue_type"])


def downgrade() -> None:
    op.drop_table("amazon_recon_issues")
    op.drop_table("amazon_order_rows")
    op.drop_table("amazon_summaries")
    op.drop_table("amazon_reports")
