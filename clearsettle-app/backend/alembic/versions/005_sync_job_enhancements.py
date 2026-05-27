"""Sync job enhancements + sync_logs table

Changes to sync_jobs
--------------------
New columns:
  company_id        UUID FK → companies.id   (nullable; back-fill via connection JOIN)
  platform          VARCHAR(50)              (denormalized for dashboard queries)
  triggered_by      VARCHAR(50) DEFAULT 'manual'
  duration_seconds  FLOAT                    (computed on job finish)
  scheduled_at      TIMESTAMP                (reserved for future scheduler)
  retry_count       INTEGER NOT NULL DEFAULT 0
  max_retries       INTEGER NOT NULL DEFAULT 3
  records_created   INTEGER NOT NULL DEFAULT 0
  records_updated   INTEGER NOT NULL DEFAULT 0
  job_options_json  TEXT                     (JSON options passed to handler)

New indexes:
  ix_sj_company_id         sync_jobs(company_id)
  ix_sj_platform           sync_jobs(platform)
  ix_sj_status_scheduled   sync_jobs(status, scheduled_at)  — future scheduler

New table sync_logs
-------------------
  id           UUID PK
  job_id       UUID FK → sync_jobs.id  ON DELETE CASCADE
  level        VARCHAR(20) NOT NULL   (debug|info|warning|error)
  message      TEXT        NOT NULL
  context_json TEXT                   (optional JSON context)
  created_at   TIMESTAMP   NOT NULL   DEFAULT NOW()

Revision ID: 005
Revises: 004
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New columns on sync_jobs ─────────────────────────────────────────────
    op.add_column("sync_jobs",
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"),
                  nullable=True))

    op.add_column("sync_jobs",
        sa.Column("platform", sa.String(50), nullable=True))

    op.add_column("sync_jobs",
        sa.Column("triggered_by", sa.String(50), nullable=False,
                  server_default="manual"))

    op.add_column("sync_jobs",
        sa.Column("duration_seconds", sa.Float(), nullable=True))

    op.add_column("sync_jobs",
        sa.Column("scheduled_at", sa.DateTime(), nullable=True))

    op.add_column("sync_jobs",
        sa.Column("retry_count", sa.Integer(), nullable=False,
                  server_default="0"))

    op.add_column("sync_jobs",
        sa.Column("max_retries", sa.Integer(), nullable=False,
                  server_default="3"))

    op.add_column("sync_jobs",
        sa.Column("records_created", sa.Integer(), nullable=False,
                  server_default="0"))

    op.add_column("sync_jobs",
        sa.Column("records_updated", sa.Integer(), nullable=False,
                  server_default="0"))

    op.add_column("sync_jobs",
        sa.Column("job_options_json", sa.Text(), nullable=True))

    # ── Back-fill company_id + platform from platform_connections ────────────
    op.execute("""
        UPDATE sync_jobs sj
        SET company_id = pc.company_id,
            platform   = pc.platform
        FROM platform_connections pc
        WHERE pc.id = sj.connection_id
    """)

    # ── Indexes on sync_jobs ─────────────────────────────────────────────────
    op.create_index("ix_sj_company_id",       "sync_jobs", ["company_id"])
    op.create_index("ix_sj_platform",         "sync_jobs", ["platform"])
    op.create_index("ix_sj_status_scheduled", "sync_jobs", ["status", "scheduled_at"])

    # ── sync_logs table ──────────────────────────────────────────────────────
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("sync_jobs.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("level",        sa.String(20), nullable=False),
        sa.Column("message",      sa.Text(),     nullable=False),
        sa.Column("context_json", sa.Text(),     nullable=True),
        sa.Column("created_at",   sa.DateTime(), nullable=False,
                  server_default=sa.text("NOW()")),
    )
    op.create_index("ix_sl_job_id", "sync_logs", ["job_id"])


def downgrade() -> None:
    op.drop_table("sync_logs")

    op.drop_index("ix_sj_status_scheduled", table_name="sync_jobs")
    op.drop_index("ix_sj_platform",         table_name="sync_jobs")
    op.drop_index("ix_sj_company_id",       table_name="sync_jobs")

    for col in [
        "job_options_json", "records_updated", "records_created",
        "max_retries", "retry_count", "scheduled_at", "duration_seconds",
        "triggered_by", "platform", "company_id",
    ]:
        op.drop_column("sync_jobs", col)
