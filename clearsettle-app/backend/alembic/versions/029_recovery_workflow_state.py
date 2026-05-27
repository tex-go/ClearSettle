"""Phase 1: add source + workflow_state to discrepancy_events.

source   — which system created this discrepancy (settlement_run | vendor_run |
            file_parse | leakage_audit | manual).  Unifies the three independent
            detection pipelines under one tracking column.

workflow_state — explicit lifecycle: detected → reviewed → filed →
                 acknowledged → resolved | rejected | dismissed.
                 Replaces the ambiguous boolean is_resolved flag.

filed_at / filed_by — timestamp + user who promoted the item to FILED state.

Revision ID: 029
Revises: 028
Create Date: 2026-05-27
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "029"
down_revision = "028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── source column ─────────────────────────────────────────────────────────
    op.add_column(
        "discrepancy_events",
        sa.Column(
            "source",
            sa.String(30),
            nullable=False,
            server_default="settlement_run",
        ),
    )

    # ── workflow_state column ─────────────────────────────────────────────────
    # Derives initial value from existing is_resolved boolean:
    #   is_resolved = True  → resolved
    #   is_resolved = False → detected
    op.add_column(
        "discrepancy_events",
        sa.Column(
            "workflow_state",
            sa.String(30),
            nullable=False,
            server_default="detected",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE discrepancy_events "
            "SET workflow_state = CASE WHEN is_resolved THEN 'resolved' ELSE 'detected' END"
        )
    )

    # ── filing metadata ───────────────────────────────────────────────────────
    op.add_column(
        "discrepancy_events",
        sa.Column("filed_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "discrepancy_events",
        sa.Column(
            "filed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── index on (company_id, workflow_state) for Recovery Center queries ─────
    op.create_index(
        "ix_discrepancy_events_company_state",
        "discrepancy_events",
        ["company_id", "workflow_state"],
    )

    # ── index on source for filtering by pipeline ─────────────────────────────
    op.create_index(
        "ix_discrepancy_events_source",
        "discrepancy_events",
        ["source"],
    )


def downgrade() -> None:
    op.drop_index("ix_discrepancy_events_source", "discrepancy_events")
    op.drop_index("ix_discrepancy_events_company_state", "discrepancy_events")
    op.drop_column("discrepancy_events", "filed_by")
    op.drop_column("discrepancy_events", "filed_at")
    op.drop_column("discrepancy_events", "workflow_state")
    op.drop_column("discrepancy_events", "source")
