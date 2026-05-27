"""Extend rules table with playbook / legal columns and seed conditions

New columns on rules
--------------------
verdict           — dispute outcome type (AUTO-DISPUTE, GST RECOVERY, INVESTIGATE, etc.)
legal_basis       — applicable law / contract clause
evidence_json     — JSON array of evidence documents required
dispute_window    — human-readable dispute window string
success_rate_pct  — historical success rate (nullable)
recovery_min      — min expected recovery amount in INR (nullable)
recovery_max      — max expected recovery amount in INR (nullable)
auto_raise        — whether the engine auto-raises a dispute (default false)
playbook_notes    — immediate action description

Changes
-------
- Updates all 8 existing global rules with playbook metadata
- Seeds conditions for all 8 existing rules
- Inserts 3 additional playbook rules (FBA Weight, SPF Coverage, Unmatched Bank Credit)
- Seeds conditions for the 3 new rules

Revision ID: 012
Revises: 011
Create Date: 2026-05-18
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add new columns ───────────────────────────────────────────────────────
    op.add_column("rules", sa.Column("verdict",          sa.String(50),      nullable=True))
    op.add_column("rules", sa.Column("legal_basis",      sa.Text,            nullable=True))
    op.add_column("rules", sa.Column("evidence_json",    sa.Text,            server_default="[]", nullable=True))
    op.add_column("rules", sa.Column("dispute_window",   sa.String(100),     nullable=True))
    op.add_column("rules", sa.Column("success_rate_pct", sa.Numeric(5, 1),   nullable=True))
    op.add_column("rules", sa.Column("recovery_min",     sa.Numeric(12, 2),  nullable=True))
    op.add_column("rules", sa.Column("recovery_max",     sa.Numeric(12, 2),  nullable=True))
    op.add_column("rules", sa.Column("auto_raise",       sa.Boolean,         nullable=False, server_default="false"))
    op.add_column("rules", sa.Column("playbook_notes",   sa.Text,            nullable=True))

    # ── Update existing 8 global rules with playbook metadata ─────────────────
    op.execute("""
        UPDATE rules SET
            verdict = 'AUTO-DISPUTE',
            legal_basis = 'Consumer Protection Act 2019 § 2(47) — unfair trade practice',
            evidence_json = '["Settlement PDF", "Published rate screenshot", "Order count proof"]',
            dispute_window = '90 days from settlement date',
            success_rate_pct = 92.0,
            recovery_min = 8000,
            recovery_max = 55000,
            auto_raise = true,
            playbook_notes = 'Freeze settlement, auto-generate dispute with rate evidence'
        WHERE name = 'Commission Overcharge' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'AUTO-DISPUTE',
            legal_basis = 'RBI Settlement Circular 2022 — timely payout obligation',
            evidence_json = '["Settlement closure report", "Bank statement", "Payout history"]',
            dispute_window = '14 days from settlement close',
            success_rate_pct = 85.0,
            recovery_min = 5000,
            recovery_max = 100000,
            auto_raise = true,
            playbook_notes = 'Flag missing payout, escalate to platform finance team'
        WHERE name = 'Missing Payout' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'AUTO-DISPUTE',
            legal_basis = 'Indian Contract Act 1872 — unjust enrichment',
            evidence_json = '["Settlement line items", "Duplicate reference proof"]',
            dispute_window = '60 days from settlement',
            success_rate_pct = 97.0,
            recovery_min = 500,
            recovery_max = 8000,
            auto_raise = true,
            playbook_notes = 'Auto-raise duplicate deduction dispute with evidence'
        WHERE name = 'Duplicate Deduction' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'GST RECOVERY',
            legal_basis = 'Income Tax Act 1961 § 206C — TCS credit mandatory',
            evidence_json = '["Settlement TCS summary", "Form 26AS", "GSTR-2A extract"]',
            dispute_window = '2 years (Income Tax filing period)',
            success_rate_pct = 100.0,
            recovery_min = 5000,
            recovery_max = 42000,
            auto_raise = false,
            playbook_notes = 'Flag for CA review, generate reconciliation statement'
        WHERE name = 'TCS Rate Mismatch' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'AUTO-DISPUTE',
            legal_basis = 'Indian Contract Act 1872 § 74 — penalty must be reasonable',
            evidence_json = '["Settlement with penalty line", "No prior notice proof"]',
            dispute_window = '60 days from settlement',
            success_rate_pct = 88.0,
            recovery_min = 320,
            recovery_max = 2400,
            auto_raise = true,
            playbook_notes = 'Flag settlement, draft penalty reversal letter'
        WHERE name = 'Penalty Overcharge' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'LISTING ALERT',
            legal_basis = 'N/A — preventive monitoring alert',
            evidence_json = '["Return reason breakdown", "Category benchmark data"]',
            dispute_window = 'Ongoing monitoring',
            success_rate_pct = NULL,
            recovery_min = NULL,
            recovery_max = NULL,
            auto_raise = false,
            playbook_notes = 'Flag SKU for listing audit, review size chart and product images'
        WHERE name = 'High Return Rate Alert' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'AUTO-DISPUTE',
            legal_basis = 'RBI Settlement Guidelines — 5-7 day mandatory payout window',
            evidence_json = '["Settlement closure timestamp", "Bank credit date", "Platform SLA document"]',
            dispute_window = '7 days from settlement close',
            success_rate_pct = 80.0,
            recovery_min = 1000,
            recovery_max = 50000,
            auto_raise = true,
            playbook_notes = 'Alert seller, send formal payout delay notice to platform'
        WHERE name = 'Payout Delay' AND company_id IS NULL
    """)

    op.execute("""
        UPDATE rules SET
            verdict = 'GST RECOVERY',
            legal_basis = 'GST Act 2017 — GSTR-2A reconciliation obligation',
            evidence_json = '["Settlement fee breakdown", "GSTR-2A extract", "GSTR-3B filing"]',
            dispute_window = '2 years',
            success_rate_pct = 90.0,
            recovery_min = 2000,
            recovery_max = 30000,
            auto_raise = false,
            playbook_notes = 'Flag for CA review, file rectification in GSTR-3B next cycle'
        WHERE name = 'GST Discrepancy' AND company_id IS NULL
    """)

    # ── Seed conditions for the 8 existing global rules ───────────────────────
    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'fee_rate_pct', 'gt', '15', 'number',
               'Charged commission rate exceeds 15% published maximum'
        FROM rules WHERE name = 'Commission Overcharge' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'settlement_status', 'eq', 'closed', 'string',
               'Settlement must be in closed state'
        FROM rules WHERE name = 'Missing Payout' AND company_id IS NULL
    """)
    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'payout_amount', 'eq', '0', 'number',
               'No payout recorded for this settlement'
        FROM rules WHERE name = 'Missing Payout' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'deduction_count', 'gte', '2', 'number',
               'Same deduction reference appears 2 or more times'
        FROM rules WHERE name = 'Duplicate Deduction' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'variance_pct', 'gt', '0.1', 'number',
               'TCS variance exceeds 0.1% tolerance of taxable value'
        FROM rules WHERE name = 'TCS Rate Mismatch' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'penalty_amount', 'gt', '5000', 'number',
               'Penalty charge exceeds ₹5,000 contractual threshold'
        FROM rules WHERE name = 'Penalty Overcharge' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'return_rate_pct', 'gt', '20', 'number',
               'Return rate exceeds 20% acceptable threshold'
        FROM rules WHERE name = 'High Return Rate Alert' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'days_since_close', 'gt', '7', 'number',
               'Payout delayed more than 7 days after settlement close'
        FROM rules WHERE name = 'Payout Delay' AND company_id IS NULL
    """)
    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'payout_received', 'eq', 'false', 'boolean',
               'Payout has not yet been received'
        FROM rules WHERE name = 'Payout Delay' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'variance_amount', 'gt', '1.0', 'number',
               'GST variance exceeds ₹1 tolerance'
        FROM rules WHERE name = 'GST Discrepancy' AND company_id IS NULL
    """)

    # ── Insert 3 additional playbook rules ────────────────────────────────────
    op.execute("""
        INSERT INTO rules (
            name, description, category, rule_type, severity, priority,
            platform, condition_logic, parameters_json, recovery_metadata_json,
            verdict, legal_basis, evidence_json, dispute_window,
            success_rate_pct, recovery_min, recovery_max, auto_raise, playbook_notes
        ) VALUES (
            'FBA Weight/Dimension Overcharge',
            'Shipping cost implies billed weight is more than 10% above registered product dimensions',
            'fees', 'custom', 'warning', 15,
            'amazon', 'all', '{"weight_tolerance_pct": 10}',
            '{"action": "dispute", "template": "fba_weight", "recovery_days": 180}',
            'AUTO-DISPUTE',
            'Amazon Seller Agreement § 8.4 — accurate billing obligation',
            '["Product weight certificate", "Shipping invoice", "FBA fee breakdown"]',
            '180 days (Amazon-specific extended window)',
            76.0, 2000, 18000, true,
            'Generate weight discrepancy report, raise with Amazon SPN'
        ),
        (
            'Return Without SPF Coverage',
            'Platform charges return shipping despite active Seller Protection Fund coverage',
            'fees', 'custom', 'warning', 20,
            NULL, 'all', '{}',
            '{"action": "dispute", "template": "spf_coverage", "recovery_days": 45}',
            'AUTO-DISPUTE',
            'Platform seller agreement — SPF coverage terms',
            '["SPF enrollment certificate", "Return shipping charge", "Policy document"]',
            '45 days from return date',
            94.0, 80, 400, true,
            'Auto-dispute with SPF enrollment proof'
        ),
        (
            'Unmatched Bank Credit',
            'Bank credit above ₹5,000 with no matching settlement ID in the register',
            'custom', 'custom', 'warning', 60,
            NULL, 'all', '{"min_amount": 5000}',
            '{"action": "investigate", "template": "unmatched_credit"}',
            'INVESTIGATE',
            'FEMA 1999 — unexplained foreign credits',
            '["Bank statement", "Settlement register", "Platform payment advice"]',
            '30 days from credit date',
            NULL, NULL, NULL, false,
            'Flag for manual review, contact platform finance team'
        )
    """)

    # ── Seed actions for new rules ─────────────────────────────────────────────
    op.execute("""
        INSERT INTO rule_actions (rule_id, action_type, action_order, parameters_json)
        SELECT id, 'create_discrepancy', 1, '{"auto_log": true}'
        FROM rules
        WHERE company_id IS NULL AND name IN (
            'FBA Weight/Dimension Overcharge',
            'Return Without SPF Coverage'
        )
    """)

    op.execute("""
        INSERT INTO rule_actions (rule_id, action_type, action_order, parameters_json)
        SELECT id, 'create_alert', 1, '{"notify": true}'
        FROM rules
        WHERE company_id IS NULL AND name = 'Unmatched Bank Credit'
    """)

    # ── Seed conditions for 3 new rules ───────────────────────────────────────
    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'weight_ratio', 'gt', '1.1', 'number',
               'Billed weight ratio exceeds 1.1x registered weight'
        FROM rules WHERE name = 'FBA Weight/Dimension Overcharge' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'spf_active', 'eq', 'true', 'boolean',
               'Seller Protection Fund is active'
        FROM rules WHERE name = 'Return Without SPF Coverage' AND company_id IS NULL
    """)
    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'return_shipping_charged', 'eq', 'true', 'boolean',
               'Return shipping was charged despite SPF coverage'
        FROM rules WHERE name = 'Return Without SPF Coverage' AND company_id IS NULL
    """)

    op.execute("""
        INSERT INTO rule_conditions (rule_id, field, operator, value, value_type, description)
        SELECT id, 'credit_amount', 'gt', '5000', 'number',
               'Bank credit exceeds ₹5,000 threshold'
        FROM rules WHERE name = 'Unmatched Bank Credit' AND company_id IS NULL
    """)


def downgrade() -> None:
    # Remove conditions for rules we seeded (by rule name match)
    op.execute("""
        DELETE FROM rule_conditions
        WHERE rule_id IN (
            SELECT id FROM rules WHERE company_id IS NULL AND name IN (
                'Commission Overcharge', 'Missing Payout', 'Duplicate Deduction',
                'TCS Rate Mismatch', 'Penalty Overcharge', 'High Return Rate Alert',
                'Payout Delay', 'GST Discrepancy',
                'FBA Weight/Dimension Overcharge', 'Return Without SPF Coverage',
                'Unmatched Bank Credit'
            )
        )
    """)
    # Remove the 3 new rules
    op.execute("""
        DELETE FROM rules WHERE company_id IS NULL AND name IN (
            'FBA Weight/Dimension Overcharge', 'Return Without SPF Coverage',
            'Unmatched Bank Credit'
        )
    """)
    # Drop the new columns
    for col in (
        "verdict", "legal_basis", "evidence_json", "dispute_window",
        "success_rate_pct", "recovery_min", "recovery_max", "auto_raise", "playbook_notes",
    ):
        op.drop_column("rules", col)
