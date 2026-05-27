"""Platform onboarding tables

New tables
----------
onboarding_sessions
  Top-level session tracking a company's activation for one marketplace platform.
  Status lifecycle: created → in_progress → completed | failed | abandoned
  Links to platform_connections once the OAuth/API-key step completes.

onboarding_steps
  One row per step within a session.  8 built-in steps in order:
    1 company_profile        — verify company GSTIN, address, contact
    2 marketplace_selection  — choose which marketplace(s) to connect
    3 platform_connection    — OAuth flow or API key entry
    4 credential_verification — live call to marketplace API to confirm access
    5 initial_sync           — trigger first data pull
    6 settlement_ingestion   — confirm at least one settlement is ingested
    7 reconciliation_activation — run first reconciliation pass
    8 dashboard_activation   — KPI aggregation and dashboard readiness check

onboarding_events
  Append-only audit trail of everything that happens during a session.

onboarding_checkpoints
  Saved state snapshots that allow retry/resume without data loss.
  UNIQUE (session_id, step_name) — one checkpoint per step.

Revision ID: 010
Revises: 009
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── onboarding_sessions ───────────────────────────────────────────────────
    op.create_table(
        "onboarding_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False, server_default="amazon"),

        sa.Column("status",       sa.String(30), nullable=False, server_default="created"),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("completed_at", sa.DateTime,   nullable=True),

        sa.Column("connection_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("platform_connections.id", ondelete="SET NULL"), nullable=True),

        sa.Column("metadata_json", sa.Text, server_default="{}"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_obs_company_id", "onboarding_sessions", ["company_id"])
    op.create_index("ix_obs_status",     "onboarding_sessions", ["status"])

    # ── onboarding_steps ──────────────────────────────────────────────────────
    op.create_table(
        "onboarding_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("onboarding_sessions.id", ondelete="CASCADE"), nullable=False),

        sa.Column("step_name",     sa.String(100), nullable=False),
        sa.Column("step_order",    sa.Integer,     nullable=False),
        sa.Column("status",        sa.String(30),  nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer,     nullable=False, server_default="0"),

        sa.Column("started_at",    sa.DateTime, nullable=True),
        sa.Column("completed_at",  sa.DateTime, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("result_json",   sa.Text,        nullable=True),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_obstep_session_id", "onboarding_steps", ["session_id"])
    op.create_index("ix_obstep_status",     "onboarding_steps", ["status"])

    # ── onboarding_events ─────────────────────────────────────────────────────
    op.create_table(
        "onboarding_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("onboarding_sessions.id", ondelete="CASCADE"), nullable=False),

        sa.Column("event_type",   sa.String(100), nullable=False),
        sa.Column("step_name",    sa.String(100), nullable=True),
        sa.Column("description",  sa.String(500), nullable=True),
        sa.Column("payload_json", sa.Text,        nullable=True),
        sa.Column("triggered_by", sa.String(50),  server_default="system"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_obev_session_id",  "onboarding_events", ["session_id"])
    op.create_index("ix_obev_event_type",  "onboarding_events", ["event_type"])
    op.create_index("ix_obev_created_at",  "onboarding_events", ["created_at"])

    # ── onboarding_checkpoints ────────────────────────────────────────────────
    op.create_table(
        "onboarding_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("onboarding_sessions.id", ondelete="CASCADE"), nullable=False),

        sa.Column("step_name",  sa.String(100), nullable=False),
        sa.Column("data_json",  sa.Text,        nullable=False, server_default="{}"),

        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),

        sa.UniqueConstraint("session_id", "step_name", name="uq_oc_session_step"),
    )
    op.create_index("ix_obcp_session_id", "onboarding_checkpoints", ["session_id"])


def downgrade() -> None:
    op.drop_table("onboarding_checkpoints")
    op.drop_table("onboarding_events")
    op.drop_table("onboarding_steps")
    op.drop_table("onboarding_sessions")
