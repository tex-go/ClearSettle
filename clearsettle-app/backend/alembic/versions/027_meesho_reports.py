"""Meesho payment report tables.

Revision ID: 027
Revises: 026
Create Date: 2026-05-22
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meesho_reports",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_id",      postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename",        sa.String(255), nullable=False),
        sa.Column("original_name",   sa.String(255), nullable=False),
        sa.Column("file_size_bytes", sa.Integer,     nullable=True),
        sa.Column("file_hash",       sa.String(64),  nullable=True),
        sa.Column("report_type",     sa.String(30),  nullable=False, server_default="payment_report"),
        sa.Column("status",          sa.String(50),  nullable=False, server_default="pending"),
        sa.Column("error_message",   sa.Text,        nullable=True),
        sa.Column("report_period",   sa.String(100), nullable=True),
        sa.Column("row_count",       sa.Integer,     nullable=True),
        sa.Column("uploaded_at",     sa.DateTime,    nullable=False),
        sa.Column("processed_at",    sa.DateTime,    nullable=True),
    )
    op.create_index("ix_meesho_reports_company_id", "meesho_reports", ["company_id"])
    op.create_index("ix_meesho_reports_file_hash",  "meesho_reports", ["file_hash"])

    op.create_table(
        "meesho_summaries",
        sa.Column("id",          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",   postgresql.UUID(as_uuid=True), sa.ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("company_id",  postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gross_sales",             sa.Numeric(18, 2), nullable=True),
        sa.Column("customer_paid_total",     sa.Numeric(18, 2), nullable=True),
        sa.Column("returns_value",           sa.Numeric(18, 2), nullable=True),
        sa.Column("cancellations_value",     sa.Numeric(18, 2), nullable=True),
        sa.Column("net_sales",               sa.Numeric(18, 2), nullable=True),
        sa.Column("commission",              sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_charges",        sa.Numeric(18, 2), nullable=True),
        sa.Column("reverse_shipping",        sa.Numeric(18, 2), nullable=True),
        sa.Column("gst_on_commission",       sa.Numeric(18, 2), nullable=True),
        sa.Column("tcs",                     sa.Numeric(18, 2), nullable=True),
        sa.Column("other_deductions",        sa.Numeric(18, 2), nullable=True),
        sa.Column("total_deductions",        sa.Numeric(18, 2), nullable=True),
        sa.Column("net_earnings",            sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_paid",             sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_pending",          sa.Numeric(18, 2), nullable=True),
        sa.Column("total_orders",            sa.Integer, nullable=True),
        sa.Column("delivered_orders",        sa.Integer, nullable=True),
        sa.Column("returned_orders",         sa.Integer, nullable=True),
        sa.Column("cancelled_orders",        sa.Integer, nullable=True),
        sa.Column("pending_orders",          sa.Integer, nullable=True),
        sa.Column("return_rate_pct",         sa.Numeric(6, 3), nullable=True),
        sa.Column("cancellation_rate_pct",   sa.Numeric(6, 3), nullable=True),
        sa.Column("effective_commission_pct",sa.Numeric(6, 3), nullable=True),
    )
    op.create_index("ix_meesho_summaries_company_id", "meesho_summaries", ["company_id"])

    op.create_table(
        "meesho_order_rows",
        sa.Column("id",               postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",        postgresql.UUID(as_uuid=True), sa.ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id",         sa.String(100), nullable=True),
        sa.Column("sub_order_id",     sa.String(100), nullable=True),
        sa.Column("order_date",       sa.Date,        nullable=True),
        sa.Column("payment_date",     sa.Date,        nullable=True),
        sa.Column("product_name",     sa.String(500), nullable=True),
        sa.Column("sku",              sa.String(200), nullable=True),
        sa.Column("category",         sa.String(200), nullable=True),
        sa.Column("quantity",         sa.Integer,     nullable=True),
        sa.Column("selling_price",    sa.Numeric(14, 2), nullable=True),
        sa.Column("mrp",              sa.Numeric(14, 2), nullable=True),
        sa.Column("customer_paid",    sa.Numeric(18, 2), nullable=True),
        sa.Column("order_amount",     sa.Numeric(18, 2), nullable=True),
        sa.Column("commission_rate",  sa.Numeric(6, 3),  nullable=True),
        sa.Column("commission",       sa.Numeric(18, 2), nullable=True),
        sa.Column("shipping_charges", sa.Numeric(18, 2), nullable=True),
        sa.Column("reverse_shipping", sa.Numeric(18, 2), nullable=True),
        sa.Column("gst_on_commission",sa.Numeric(18, 2), nullable=True),
        sa.Column("tcs",              sa.Numeric(18, 2), nullable=True),
        sa.Column("other_deductions", sa.Numeric(18, 2), nullable=True),
        sa.Column("net_payment",      sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_net",     sa.Numeric(18, 2), nullable=True),
        sa.Column("payment_variance", sa.Numeric(18, 2), nullable=True),
        sa.Column("order_status",     sa.String(50),  nullable=True),
        sa.Column("payment_status",   sa.String(50),  nullable=True),
    )
    op.create_index("ix_meesho_order_rows_report_id",  "meesho_order_rows", ["report_id"])
    op.create_index("ix_meesho_order_rows_company_id", "meesho_order_rows", ["company_id"])
    op.create_index("ix_meesho_order_rows_order_id",   "meesho_order_rows", ["order_id"])
    op.create_index("ix_meesho_order_rows_sku",        "meesho_order_rows", ["sku"])

    op.create_table(
        "meesho_recon_issues",
        sa.Column("id",              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id",       postgresql.UUID(as_uuid=True), sa.ForeignKey("meesho_reports.id", ondelete="CASCADE"), nullable=False),
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
    op.create_index("ix_meesho_recon_issues_report_id",  "meesho_recon_issues", ["report_id"])
    op.create_index("ix_meesho_recon_issues_company_id", "meesho_recon_issues", ["company_id"])
    op.create_index("ix_meesho_recon_issues_issue_type", "meesho_recon_issues", ["issue_type"])


def downgrade() -> None:
    op.drop_table("meesho_recon_issues")
    op.drop_table("meesho_order_rows")
    op.drop_table("meesho_summaries")
    op.drop_table("meesho_reports")
