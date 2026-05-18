"""Reconciliation engine tables

New tables
----------
reconciliation_rules
  One row per detection rule. Global rules (company_id IS NULL) apply to all
  companies. Parameters are stored as JSON for flexible threshold configuration.

reconciliation_results
  One row per engine run for a given settlement (multiple runs allowed for
  audit trail). Links to the settlement and records aggregate counts/amounts.

discrepancy_events
  One row per individual discrepancy detected in a reconciliation run.
  Tracks type, severity, expected vs actual amounts, and resolution state.

Seeded default rules
---------------------
Seven global rules are inserted at migration time:
  missing_payout, payout_amount_mismatch, referral_fee_overcharge,
  fba_fee_overcharge, duplicate_deduction, unexpected_fee, penalty_mismatch

Revision ID: 007
Revises: 006
Create Date: 2026-05-17
"""
from typing import Sequence, Union
import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── reconciliation_rules ─────────────────────────────────────────────────
    op.create_table(
        "reconciliation_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("platform", sa.String(50), nullable=True),

        sa.Column("rule_type",       sa.String(100), nullable=False),
        sa.Column("rule_name",       sa.String(255), nullable=False),
        sa.Column("description",     sa.String(500)),
        sa.Column("parameters_json", sa.Text(), server_default="{}"),
        sa.Column("severity",        sa.String(20),  nullable=False, server_default="warning"),
        sa.Column("is_active",       sa.Boolean(),   nullable=False, server_default=sa.true()),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_recon_rules_company_id", "reconciliation_rules", ["company_id"])
    op.create_index("ix_recon_rules_rule_type",  "reconciliation_rules", ["rule_type"])
    op.create_index("ix_recon_rules_is_active",  "reconciliation_rules", ["is_active"])

    # ── reconciliation_results ───────────────────────────────────────────────
    op.create_table(
        "reconciliation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="amazon"),

        sa.Column("status",                sa.String(20),     nullable=False, server_default="clean"),
        sa.Column("total_discrepancies",   sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("warning_count",         sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("critical_count",        sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("info_count",            sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("total_variance_amount", sa.Numeric(15, 4), nullable=False, server_default="0"),
        sa.Column("rules_evaluated",       sa.Integer(),      nullable=False, server_default="0"),
        sa.Column("processing_time_ms",    sa.Integer()),
        sa.Column("error_message",         sa.String(500)),
        sa.Column("metadata_json",         sa.Text()),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_recon_results_settlement_id", "reconciliation_results", ["settlement_id"])
    op.create_index("ix_recon_results_company_id",    "reconciliation_results", ["company_id"])
    op.create_index("ix_recon_results_status",        "reconciliation_results", ["status"])
    op.create_index("ix_recon_results_created_at",    "reconciliation_results", ["created_at"])

    # ── discrepancy_events ───────────────────────────────────────────────────
    op.create_table(
        "discrepancy_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("result_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reconciliation_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("settlement_transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("reconciliation_rules.id", ondelete="SET NULL"), nullable=True),

        sa.Column("platform",         sa.String(50),  nullable=False, server_default="amazon"),
        sa.Column("discrepancy_type", sa.String(100), nullable=False),
        sa.Column("severity",         sa.String(20),  nullable=False),

        sa.Column("expected_amount", sa.Numeric(15, 4)),
        sa.Column("actual_amount",   sa.Numeric(15, 4)),
        sa.Column("variance_amount", sa.Numeric(15, 4)),

        sa.Column("description",   sa.String(500), nullable=False),
        sa.Column("order_id",      sa.String(50)),
        sa.Column("fee_type",      sa.String(100)),
        sa.Column("metadata_json", sa.Text()),

        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True)),

        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_disc_events_result_id",      "discrepancy_events", ["result_id"])
    op.create_index("ix_disc_events_settlement_id",  "discrepancy_events", ["settlement_id"])
    op.create_index("ix_disc_events_transaction_id", "discrepancy_events", ["transaction_id"])
    op.create_index("ix_disc_events_company_id",     "discrepancy_events", ["company_id"])
    op.create_index("ix_disc_events_type",           "discrepancy_events", ["discrepancy_type"])
    op.create_index("ix_disc_events_severity",       "discrepancy_events", ["severity"])
    op.create_index("ix_disc_events_is_resolved",    "discrepancy_events", ["is_resolved"])
    op.create_index("ix_disc_events_order_id",       "discrepancy_events", ["order_id"])

    # ── Seed default global rules ────────────────────────────────────────────
    rules_table = sa.table(
        "reconciliation_rules",
        sa.column("id",              postgresql.UUID(as_uuid=True)),
        sa.column("company_id",      postgresql.UUID(as_uuid=True)),
        sa.column("platform",        sa.String),
        sa.column("rule_type",       sa.String),
        sa.column("rule_name",       sa.String),
        sa.column("description",     sa.String),
        sa.column("parameters_json", sa.String),
        sa.column("severity",        sa.String),
        sa.column("is_active",       sa.Boolean),
    )

    op.bulk_insert(rules_table, [
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "missing_payout",
            "rule_name":       "Missing Payout Detection",
            "description":     "Flags closed settlements that have no payout event or have a failed payout.",
            "parameters_json": "{}",
            "severity":        "critical",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "payout_amount_mismatch",
            "rule_name":       "Payout Amount Mismatch",
            "description":     "Flags when the actual payout amount differs from the settlement's fund transfer amount by more than 1%.",
            "parameters_json": '{"tolerance_pct": 0.01}',
            "severity":        "critical",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "referral_fee_overcharge",
            "rule_name":       "Referral Fee Overcharge",
            "description":     "Flags shipment transactions where the referral fee exceeds 30% of the principal amount.",
            "parameters_json": '{"max_rate": 0.30}',
            "severity":        "warning",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "fba_fee_overcharge",
            "rule_name":       "FBA Fee Overcharge",
            "description":     "Flags shipment transactions where FBA fulfillment fee per unit exceeds ₹150.",
            "parameters_json": '{"max_per_unit": 150.0}',
            "severity":        "warning",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "duplicate_deduction",
            "rule_name":       "Duplicate Deduction Detection",
            "description":     "Flags when the same fee type is charged multiple times for the same order item within a settlement.",
            "parameters_json": "{}",
            "severity":        "critical",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "unexpected_fee",
            "rule_name":       "Unexpected Fee Type",
            "description":     "Flags fee types that are not in the known/expected list for this marketplace.",
            "parameters_json": '{"allowed_fee_types": []}',
            "severity":        "info",
            "is_active":       True,
        },
        {
            "id":              uuid.uuid4(),
            "company_id":      None,
            "platform":        None,
            "rule_type":       "penalty_mismatch",
            "rule_name":       "Excessive Penalty Detection",
            "description":     "Flags service fee transactions exceeding ₹5,000 that may represent unexpected penalties.",
            "parameters_json": '{"max_service_fee": 5000.0}',
            "severity":        "warning",
            "is_active":       True,
        },
    ])


def downgrade() -> None:
    op.drop_table("discrepancy_events")
    op.drop_table("reconciliation_results")
    op.drop_table("reconciliation_rules")
