"""Vendor Reconciliation Engine — ingestion, staging, fact, leakage tables

Tables created
--------------
recon_files           — uploaded file metadata + processing status
recon_jobs            — reconciliation job (one per cycle / run)
recon_job_files       — many-to-many: which files belong to which job
stg_settlement_lines  — normalized settlement / deduction lines
stg_invoice_lines     — normalized invoice lines
stg_chargeback_lines  — normalized chargeback / penalty lines
stg_payment_lines     — normalized remittance / payment advice lines
stg_operational_lines — PO / ASN / POD / OTIF / shortage / return / damage lines
fact_reconciliation   — per-job summary (expected vs actual payout)
leakage_events        — individual leakage instances (10 types)
dim_deduction_codes   — seeded deduction-code dictionary

Revision ID: 013
Revises: 012
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── recon_files ───────────────────────────────────────────────────────────
    op.create_table(
        "recon_files",
        sa.Column("id",               sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id",       sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("filename",         sa.String(255), nullable=False),
        sa.Column("original_name",    sa.String(255), nullable=False),
        sa.Column("file_type",        sa.String(50),  nullable=False),   # settlement/invoice/chargeback/po/asn/pod/payment_advice/return/damage/shortage/otif/sku_master/deduction_dict/custom
        sa.Column("file_format",      sa.String(10),  nullable=True),    # csv/xlsx/txt/pdf
        sa.Column("file_size_bytes",  sa.Integer,     nullable=True),
        sa.Column("status",           sa.String(20),  nullable=False, server_default="pending"),  # pending/processing/processed/failed
        sa.Column("row_count",        sa.Integer,     nullable=True),
        sa.Column("error_message",    sa.Text,        nullable=True),
        sa.Column("column_map_json",  sa.Text,        nullable=True),    # user-supplied column mapping
        sa.Column("created_at",       sa.DateTime,    nullable=False, server_default=sa.text("now()")),
        sa.Column("processed_at",     sa.DateTime,    nullable=True),
    )

    # ── recon_jobs ────────────────────────────────────────────────────────────
    op.create_table(
        "recon_jobs",
        sa.Column("id",              sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id",      sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name",            sa.String(200), nullable=False),
        sa.Column("description",     sa.Text,        nullable=True),
        sa.Column("period_start",    sa.Date,        nullable=True),
        sa.Column("period_end",      sa.Date,        nullable=True),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="draft"),   # draft/queued/running/completed/failed
        sa.Column("platform",        sa.String(50),  nullable=True),    # amazon/flipkart/meesho/null=generic
        sa.Column("currency",        sa.String(3),   nullable=False, server_default="INR"),
        # results (populated after run)
        sa.Column("expected_payout",  sa.Numeric(16, 2), nullable=True),
        sa.Column("actual_payout",    sa.Numeric(16, 2), nullable=True),
        sa.Column("variance_amount",  sa.Numeric(16, 2), nullable=True),
        sa.Column("variance_pct",     sa.Numeric(8,  4),  nullable=True),
        sa.Column("total_leakage",    sa.Numeric(16, 2), nullable=True),
        sa.Column("leakage_count",    sa.Integer,     nullable=True),
        sa.Column("disputable_amount",sa.Numeric(16, 2), nullable=True),
        sa.Column("summary_json",     sa.Text,        nullable=True),   # per-detector breakdown
        sa.Column("error_message",    sa.Text,        nullable=True),
        sa.Column("created_at",       sa.DateTime,    nullable=False, server_default=sa.text("now()")),
        sa.Column("started_at",       sa.DateTime,    nullable=True),
        sa.Column("completed_at",     sa.DateTime,    nullable=True),
    )

    # ── recon_job_files ───────────────────────────────────────────────────────
    op.create_table(
        "recon_job_files",
        sa.Column("id",       sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",   sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",  sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_role",sa.String(50), nullable=False),   # primary role in this job
        sa.UniqueConstraint("job_id", "file_id", name="uq_recon_job_file"),
    )

    # ── stg_settlement_lines ──────────────────────────────────────────────────
    op.create_table(
        "stg_settlement_lines",
        sa.Column("id",                sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",            sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",           sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("settlement_id",     sa.String(100), nullable=True),
        sa.Column("transaction_date",  sa.Date,        nullable=True),
        sa.Column("reference_number",  sa.String(150), nullable=True),
        sa.Column("invoice_number",    sa.String(150), nullable=True),
        sa.Column("po_number",         sa.String(150), nullable=True),
        sa.Column("deduction_code",    sa.String(100), nullable=True),
        sa.Column("deduction_reason",  sa.String(255), nullable=True),
        sa.Column("line_type",         sa.String(50),  nullable=True),  # invoice/deduction/accrual/reversal/adjustment
        sa.Column("gross_amount",      sa.Numeric(16, 2), nullable=True),
        sa.Column("deduction_amount",  sa.Numeric(16, 2), nullable=True),
        sa.Column("accrual_amount",    sa.Numeric(16, 2), nullable=True),
        sa.Column("reversal_amount",   sa.Numeric(16, 2), nullable=True),
        sa.Column("net_amount",        sa.Numeric(16, 2), nullable=True),
        sa.Column("tax_amount",        sa.Numeric(16, 2), nullable=True),
        sa.Column("currency",          sa.String(3),   nullable=True, server_default="INR"),
        sa.Column("payment_reference", sa.String(150), nullable=True),
        sa.Column("sku",               sa.String(100), nullable=True),
        sa.Column("asin",              sa.String(20),  nullable=True),
        sa.Column("raw_row_json",      sa.Text,        nullable=True),
        sa.Column("created_at",        sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── stg_invoice_lines ─────────────────────────────────────────────────────
    op.create_table(
        "stg_invoice_lines",
        sa.Column("id",             sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",         sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",        sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("invoice_number", sa.String(150), nullable=True, index=True),
        sa.Column("invoice_date",   sa.Date,        nullable=True),
        sa.Column("po_number",      sa.String(150), nullable=True, index=True),
        sa.Column("sku",            sa.String(100), nullable=True),
        sa.Column("asin",           sa.String(20),  nullable=True),
        sa.Column("quantity",       sa.Numeric(12, 3), nullable=True),
        sa.Column("unit_price",     sa.Numeric(14, 4), nullable=True),
        sa.Column("invoice_total",  sa.Numeric(16, 2), nullable=True),
        sa.Column("tax_amount",     sa.Numeric(16, 2), nullable=True),
        sa.Column("discount_amount",sa.Numeric(16, 2), nullable=True),
        sa.Column("currency",       sa.String(3),   nullable=True, server_default="INR"),
        sa.Column("vendor_code",    sa.String(100), nullable=True),
        sa.Column("raw_row_json",   sa.Text,        nullable=True),
        sa.Column("created_at",     sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── stg_chargeback_lines ──────────────────────────────────────────────────
    op.create_table(
        "stg_chargeback_lines",
        sa.Column("id",               sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",           sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",          sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("chargeback_id",    sa.String(150), nullable=True),
        sa.Column("deduction_code",   sa.String(100), nullable=True, index=True),
        sa.Column("deduction_reason", sa.String(255), nullable=True),
        sa.Column("po_number",        sa.String(150), nullable=True),
        sa.Column("invoice_number",   sa.String(150), nullable=True),
        sa.Column("shipment_id",      sa.String(150), nullable=True),
        sa.Column("deduction_amount", sa.Numeric(16, 2), nullable=True),
        sa.Column("dispute_status",   sa.String(50),  nullable=True),  # open/disputed/recovered/waived
        sa.Column("created_date",     sa.Date,        nullable=True),
        sa.Column("dispute_deadline", sa.Date,        nullable=True),
        sa.Column("raw_row_json",     sa.Text,        nullable=True),
        sa.Column("created_at",       sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── stg_payment_lines ─────────────────────────────────────────────────────
    op.create_table(
        "stg_payment_lines",
        sa.Column("id",             sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",         sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",        sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("settlement_id",  sa.String(100), nullable=True, index=True),
        sa.Column("bank_reference", sa.String(150), nullable=True),
        sa.Column("paid_amount",    sa.Numeric(16, 2), nullable=True),
        sa.Column("transfer_date",  sa.Date,        nullable=True),
        sa.Column("payment_method", sa.String(50),  nullable=True),
        sa.Column("currency",       sa.String(3),   nullable=True, server_default="INR"),
        sa.Column("bank_account",   sa.String(50),  nullable=True),
        sa.Column("raw_row_json",   sa.Text,        nullable=True),
        sa.Column("created_at",     sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── stg_operational_lines ─────────────────────────────────────────────────
    # Generic table for PO/ASN/POD/OTIF/shortage/return/damage rows
    op.create_table(
        "stg_operational_lines",
        sa.Column("id",               sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",           sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id",  ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_id",          sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_files.id", ondelete="CASCADE"), nullable=True),
        sa.Column("line_category",    sa.String(30),  nullable=False, index=True),  # po/asn/pod/receiving/otif/return/damage/shortage/dispute_recovery
        sa.Column("po_number",        sa.String(150), nullable=True, index=True),
        sa.Column("invoice_number",   sa.String(150), nullable=True),
        sa.Column("shipment_id",      sa.String(150), nullable=True),
        sa.Column("claim_id",         sa.String(150), nullable=True),
        sa.Column("dispute_id",       sa.String(150), nullable=True),
        sa.Column("sku",              sa.String(100), nullable=True),
        sa.Column("asin",             sa.String(20),  nullable=True),
        # dates
        sa.Column("event_date",       sa.Date,        nullable=True),
        sa.Column("expected_date",    sa.Date,        nullable=True),
        sa.Column("actual_date",      sa.Date,        nullable=True),
        # quantities
        sa.Column("ordered_qty",      sa.Numeric(12, 3), nullable=True),
        sa.Column("shipped_qty",      sa.Numeric(12, 3), nullable=True),
        sa.Column("received_qty",     sa.Numeric(12, 3), nullable=True),
        sa.Column("short_qty",        sa.Numeric(12, 3), nullable=True),
        sa.Column("damaged_qty",      sa.Numeric(12, 3), nullable=True),
        sa.Column("return_qty",       sa.Numeric(12, 3), nullable=True),
        # financials
        sa.Column("amount",           sa.Numeric(16, 2), nullable=True),
        sa.Column("penalty_amount",   sa.Numeric(16, 2), nullable=True),
        sa.Column("recovered_amount", sa.Numeric(16, 2), nullable=True),
        # status / flags
        sa.Column("compliance_status",sa.String(50),  nullable=True),
        sa.Column("dispute_status",   sa.String(50),  nullable=True),
        sa.Column("fill_rate_pct",    sa.Numeric(6, 3), nullable=True),
        sa.Column("warehouse",        sa.String(100), nullable=True),
        sa.Column("return_reason",    sa.String(255), nullable=True),
        sa.Column("receiver_name",    sa.String(150), nullable=True),
        sa.Column("extra_json",       sa.Text,        nullable=True),  # catch-all for extra columns
        sa.Column("raw_row_json",     sa.Text,        nullable=True),
        sa.Column("created_at",       sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── fact_reconciliation ───────────────────────────────────────────────────
    op.create_table(
        "fact_reconciliation",
        sa.Column("id",                    sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",                sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_invoice_value",   sa.Numeric(16, 2), nullable=True),
        sa.Column("total_agreed_discounts",sa.Numeric(16, 2), nullable=True),
        sa.Column("total_valid_returns",   sa.Numeric(16, 2), nullable=True),
        sa.Column("total_approved_coop",   sa.Numeric(16, 2), nullable=True),
        sa.Column("total_valid_tax_adj",   sa.Numeric(16, 2), nullable=True),
        sa.Column("expected_payout",       sa.Numeric(16, 2), nullable=True),  # computed
        sa.Column("actual_payout",         sa.Numeric(16, 2), nullable=True),
        sa.Column("variance_amount",       sa.Numeric(16, 2), nullable=True),
        sa.Column("variance_pct",          sa.Numeric(8,  4),  nullable=True),
        sa.Column("total_deductions",      sa.Numeric(16, 2), nullable=True),
        sa.Column("valid_deductions",      sa.Numeric(16, 2), nullable=True),
        sa.Column("suspicious_deductions", sa.Numeric(16, 2), nullable=True),
        sa.Column("duplicate_deductions",  sa.Numeric(16, 2), nullable=True),
        sa.Column("disputable_amount",     sa.Numeric(16, 2), nullable=True),
        sa.Column("unrecovered_claims",    sa.Numeric(16, 2), nullable=True),
        sa.Column("total_leakage",         sa.Numeric(16, 2), nullable=True),
        sa.Column("leakage_by_type_json",  sa.Text,           nullable=True),
        sa.Column("computed_at",           sa.DateTime,       nullable=False, server_default=sa.text("now()")),
    )

    # ── leakage_events ────────────────────────────────────────────────────────
    op.create_table(
        "leakage_events",
        sa.Column("id",                  sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id",              sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("recon_jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("leakage_type",        sa.String(30),  nullable=False, index=True),
        # SHORT/DUPLICATE/OTIF/ACCRUAL/COOP/RETURN/DAMAGE/TIMING/TAX/DISPUTE_RECOVERY
        sa.Column("severity",            sa.String(20),  nullable=False),   # critical/warning/info
        sa.Column("reference_type",      sa.String(30),  nullable=True),    # invoice/po/chargeback/settlement/payment
        sa.Column("reference_id",        sa.String(200), nullable=True),    # document identifier
        sa.Column("po_number",           sa.String(150), nullable=True),
        sa.Column("invoice_number",      sa.String(150), nullable=True),
        sa.Column("sku",                 sa.String(100), nullable=True),
        sa.Column("deduction_code",      sa.String(100), nullable=True),
        sa.Column("amount",              sa.Numeric(16, 2), nullable=True),
        sa.Column("description",         sa.Text,        nullable=False),
        sa.Column("root_cause",          sa.Text,        nullable=True),
        sa.Column("is_disputable",       sa.Boolean,     nullable=False, server_default="false"),
        sa.Column("recovery_potential",  sa.Numeric(16, 2), nullable=True),
        sa.Column("recovery_recommendation", sa.Text,   nullable=True),
        sa.Column("evidence_json",       sa.Text,        nullable=True, server_default="[]"),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="open"),   # open/disputed/resolved/waived
        sa.Column("resolved_by",         sa.String(100), nullable=True),
        sa.Column("resolution_note",     sa.Text,        nullable=True),
        sa.Column("created_at",          sa.DateTime,    nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at",         sa.DateTime,    nullable=True),
    )

    # ── dim_deduction_codes ───────────────────────────────────────────────────
    op.create_table(
        "dim_deduction_codes",
        sa.Column("id",               sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("code",             sa.String(50),  nullable=False, unique=True),
        sa.Column("name",             sa.String(200), nullable=False),
        sa.Column("category",         sa.String(50),  nullable=False),   # fee/penalty/chargeback/coop/adjustment/tax/return/shortage
        sa.Column("is_dispute_allowed", sa.Boolean,  nullable=False, server_default="true"),
        sa.Column("severity_level",   sa.String(20),  nullable=False, server_default="warning"),
        sa.Column("description",      sa.Text,        nullable=True),
        sa.Column("platform",         sa.String(50),  nullable=True),    # null = generic
        sa.Column("created_at",       sa.DateTime,    nullable=False, server_default=sa.text("now()")),
    )

    # ── Seed dim_deduction_codes ──────────────────────────────────────────────
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('COMM_OVER', 'Commission Overcharge', 'fee', true, 'critical', 'Commission charged above contracted rate', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('DUP_DED', 'Duplicate Deduction', 'fee', true, 'critical', 'Same deduction applied more than once for the same reference', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('OTIF_PEN', 'OTIF Penalty', 'penalty', true, 'warning', 'On-Time In-Full compliance penalty', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('SHORTAGE', 'Shortage Claim', 'chargeback', true, 'critical', 'Units claimed as not received in warehouse', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('COOP', 'Co-Op / Marketing Funding', 'coop', true, 'warning', 'Cooperative marketing or promotional funding deduction', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('RETURN_DED', 'Return Deduction', 'return', true, 'warning', 'Deduction for returned goods', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('DAMAGE', 'Damage / Unsellable', 'chargeback', true, 'warning', 'Deduction for damaged or unsellable inventory at warehouse', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('ACCRUAL', 'Accrual Deduction', 'adjustment', true, 'info', 'Temporary accrual — should reverse in subsequent period', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('REVERSAL', 'Accrual Reversal', 'adjustment', false, 'info', 'Credit entry reversing a prior accrual deduction', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('TCS', 'TCS Deduction', 'tax', false, 'info', 'Tax Collected at Source per Indian Income Tax Act § 206C', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('GST_DED', 'GST Deduction', 'tax', true, 'warning', 'GST deduction — verify against GSTR-2A', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('FILL_RATE', 'Fill Rate Penalty', 'penalty', true, 'warning', 'Penalty for not meeting minimum fill rate on PO', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('LABEL_PEN', 'Labelling Penalty', 'penalty', true, 'info', 'Penalty for incorrect or missing product labels', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('PRICE_CLAIM', 'Price Protection Claim', 'chargeback', true, 'warning', 'Claim for price difference between PO and invoice', NULL)
    """)
    op.execute("""
        INSERT INTO dim_deduction_codes (code, name, category, is_dispute_allowed, severity_level, description, platform) VALUES
        ('UNKNOWN', 'Unknown / Unclassified', 'fee', true, 'critical', 'Deduction code not in the approved dictionary — investigate immediately', NULL)
    """)


def downgrade() -> None:
    op.drop_table("dim_deduction_codes")
    op.drop_table("leakage_events")
    op.drop_table("fact_reconciliation")
    op.drop_table("stg_operational_lines")
    op.drop_table("stg_payment_lines")
    op.drop_table("stg_chargeback_lines")
    op.drop_table("stg_invoice_lines")
    op.drop_table("stg_settlement_lines")
    op.drop_table("recon_job_files")
    op.drop_table("recon_jobs")
    op.drop_table("recon_files")
