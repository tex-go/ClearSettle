"""Configurable rule engine tables

New tables
----------
rules
  Generic, evaluatable rules with category, priority, and condition_logic.
  Global rules (company_id IS NULL) apply across all companies.
  Per-company rules are scoped to that company only.

rule_conditions
  One condition expression per row (field / operator / value triple).
  All conditions in a rule are ANDed (condition_logic='all') or ORed ('any').

rule_actions
  Actions to execute when a rule matches (create_discrepancy, create_alert, etc.).
  Ordered by action_order; only is_enabled=true actions fire.

rule_execution_logs
  Append-only audit log — one row per rule evaluation attempt.
  Stores the input context_json so past runs can be replayed.

company_rule_overrides
  Allows a company to override severity, priority, or parameters for any
  global rule without duplicating it.  UNIQUE (rule_id, company_id).

Seeded built-in rules
  8 default global rules covering the most common marketplace discrepancy types.

Revision ID: 009
Revises: 008
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── rules ─────────────────────────────────────────────────────────────────
    op.create_table(
        "rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),

        sa.Column("name",            sa.String(255),  nullable=False),
        sa.Column("description",     sa.String(1000), nullable=True),
        sa.Column("category",        sa.String(100),  nullable=False),
        sa.Column("rule_type",       sa.String(100),  nullable=False),
        sa.Column("severity",        sa.String(20),   nullable=False, server_default="warning"),
        sa.Column("priority",        sa.Integer,      nullable=False, server_default="100"),
        sa.Column("platform",        sa.String(50),   nullable=True),
        sa.Column("is_enabled",      sa.Boolean,      nullable=False, server_default="true"),
        sa.Column("condition_logic", sa.String(10),   nullable=False, server_default="all"),

        sa.Column("parameters_json",        sa.Text, server_default="{}"),
        sa.Column("recovery_metadata_json", sa.Text, server_default="{}"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rules_company_id", "rules", ["company_id"])
    op.create_index("ix_rules_category",   "rules", ["category"])
    op.create_index("ix_rules_rule_type",  "rules", ["rule_type"])
    op.create_index("ix_rules_is_enabled", "rules", ["is_enabled"])

    # ── rule_conditions ───────────────────────────────────────────────────────
    op.create_table(
        "rule_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),

        sa.Column("field",       sa.String(100), nullable=False),
        sa.Column("operator",    sa.String(20),  nullable=False),
        sa.Column("value",       sa.String(500), nullable=False),
        sa.Column("value_type",  sa.String(20),  nullable=False, server_default="number"),
        sa.Column("description", sa.String(200), nullable=True),
    )
    op.create_index("ix_rule_conditions_rule_id", "rule_conditions", ["rule_id"])

    # ── rule_actions ──────────────────────────────────────────────────────────
    op.create_table(
        "rule_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rules.id", ondelete="CASCADE"), nullable=False),

        sa.Column("action_type",     sa.String(100), nullable=False),
        sa.Column("action_order",    sa.Integer,     nullable=False, server_default="1"),
        sa.Column("parameters_json", sa.Text,        server_default="{}"),
        sa.Column("is_enabled",      sa.Boolean,     nullable=False, server_default="true"),
    )
    op.create_index("ix_rule_actions_rule_id",     "rule_actions", ["rule_id"])
    op.create_index("ix_rule_actions_action_type", "rule_actions", ["action_type"])

    # ── rule_execution_logs ───────────────────────────────────────────────────
    op.create_table(
        "rule_execution_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rules.id",    ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),

        sa.Column("settlement_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_json",   sa.Text,        nullable=True),

        sa.Column("matched",          sa.Boolean, nullable=False, server_default="false"),
        sa.Column("actions_executed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duration_ms",      sa.Integer, nullable=True),
        sa.Column("error_message",    sa.String(500), nullable=True),

        sa.Column("is_dry_run",   sa.Boolean,    nullable=False, server_default="false"),
        sa.Column("triggered_by", sa.String(50), nullable=False, server_default="manual"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rel_rule_id",       "rule_execution_logs", ["rule_id"])
    op.create_index("ix_rel_company_id",    "rule_execution_logs", ["company_id"])
    op.create_index("ix_rel_settlement_id", "rule_execution_logs", ["settlement_id"])
    op.create_index("ix_rel_created_at",    "rule_execution_logs", ["created_at"])

    # ── company_rule_overrides ────────────────────────────────────────────────
    op.create_table(
        "company_rule_overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rules.id",    ondelete="CASCADE"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),

        sa.Column("is_enabled",      sa.Boolean,    nullable=True),
        sa.Column("severity",        sa.String(20), nullable=True),
        sa.Column("priority",        sa.Integer,    nullable=True),
        sa.Column("parameters_json", sa.Text,       nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),

        sa.UniqueConstraint("rule_id", "company_id", name="uq_cro_rule_company"),
    )
    op.create_index("ix_cro_rule_id",    "company_rule_overrides", ["rule_id"])
    op.create_index("ix_cro_company_id", "company_rule_overrides", ["company_id"])

    # ── Seed built-in global rules ────────────────────────────────────────────
    op.execute("""
        INSERT INTO rules (name, description, category, rule_type, severity, priority,
                           condition_logic, parameters_json, recovery_metadata_json)
        VALUES
        (
            'Commission Overcharge',
            'Detects when the referral/commission fee rate exceeds the expected maximum',
            'fees', 'commission_overcharge', 'warning', 10, 'all',
            '{"max_rate_pct": 15, "fee_types": ["Commission", "ReferralFee"]}',
            '{"action": "dispute", "template": "commission_overcharge", "recovery_days": 30}'
        ),
        (
            'Missing Payout',
            'Settlement is closed but no fund transfer payout has been recorded',
            'payout', 'missing_payout', 'critical', 5, 'all',
            '{"settlement_status": "closed"}',
            '{"action": "escalate", "template": "missing_payout", "recovery_days": 14}'
        ),
        (
            'Duplicate Deduction',
            'The same fee type has been deducted more than once for the same order item',
            'fees', 'duplicate_deduction', 'critical', 8, 'all',
            '{"min_occurrences": 2}',
            '{"action": "dispute", "template": "duplicate_deduction", "recovery_days": 30}'
        ),
        (
            'TCS Rate Mismatch',
            'TCS deducted does not match the expected 1% of taxable value (Section 52 CGST)',
            'tax', 'tcs_mismatch', 'warning', 20, 'all',
            '{"expected_rate_pct": 1, "tolerance_pct": 0.1}',
            '{"action": "recommend", "template": "tcs_mismatch", "recovery_days": 90}'
        ),
        (
            'Penalty Overcharge',
            'Service/penalty fee exceeds the contractual threshold',
            'fees', 'penalty_overcharge', 'warning', 30, 'all',
            '{"max_penalty_amount": 5000}',
            '{"action": "dispute", "template": "penalty_overcharge", "recovery_days": 60}'
        ),
        (
            'High Return Rate Alert',
            'Return rate for the settlement period exceeds the acceptable threshold',
            'risk', 'high_return_rate', 'info', 50, 'all',
            '{"max_return_rate_pct": 20}',
            '{"action": "alert", "template": "high_return_rate"}'
        ),
        (
            'Payout Delay',
            'Settlement closed but payout is delayed beyond the expected settlement window',
            'payout', 'payout_delay', 'warning', 40, 'all',
            '{"max_delay_days": 7}',
            '{"action": "alert", "template": "payout_delay", "recovery_days": 7}'
        ),
        (
            'GST Discrepancy',
            'GST computed from settlement fees does not match the reported tax amount',
            'tax', 'gst_discrepancy', 'warning', 25, 'all',
            '{"tolerance_amount": 1.0}',
            '{"action": "recommend", "template": "gst_discrepancy", "recovery_days": 90}'
        )
    """)

    # Seed default actions for built-in rules
    op.execute("""
        INSERT INTO rule_actions (rule_id, action_type, action_order, parameters_json)
        SELECT id, 'create_discrepancy', 1, '{"auto_log": true}'
        FROM rules
        WHERE company_id IS NULL AND rule_type IN (
            'commission_overcharge', 'missing_payout', 'duplicate_deduction',
            'tcs_mismatch', 'penalty_overcharge', 'gst_discrepancy'
        )
    """)

    op.execute("""
        INSERT INTO rule_actions (rule_id, action_type, action_order, parameters_json)
        SELECT id, 'create_alert', 1, '{"auto_log": true}'
        FROM rules
        WHERE company_id IS NULL AND rule_type IN ('high_return_rate', 'payout_delay')
    """)

    op.execute("""
        INSERT INTO rule_actions (rule_id, action_type, action_order, parameters_json)
        SELECT id, 'recommend_recovery', 2, '{"auto_log": true}'
        FROM rules
        WHERE company_id IS NULL AND rule_type IN (
            'commission_overcharge', 'missing_payout', 'duplicate_deduction', 'penalty_overcharge'
        )
    """)


def downgrade() -> None:
    op.drop_table("company_rule_overrides")
    op.drop_table("rule_execution_logs")
    op.drop_table("rule_actions")
    op.drop_table("rule_conditions")
    op.drop_table("rules")
