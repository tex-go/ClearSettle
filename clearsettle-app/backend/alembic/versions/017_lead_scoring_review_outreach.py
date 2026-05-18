"""Lead scoring, review, and outreach fields on seller_leads.

Revision ID: 017
Revises: 016
Create Date: 2026-05-18

Adds:
  seller_leads.lead_score            NUMERIC(5,2)   — weighted 0-100 score
  seller_leads.score_breakdown_json  TEXT           — JSON factor breakdown
  seller_leads.priority_level        VARCHAR(20)    — hot | warm | cold | skip
  seller_leads.reviewed_at           TIMESTAMP      — when human reviewed
  seller_leads.reviewed_by           VARCHAR(100)   — reviewer identity
  seller_leads.outreach_status       VARCHAR(30)    — pending|ready|contacted|skipped
  seller_leads.outreach_notes        TEXT           — prep notes

Indexes added:
  ix_seller_leads_lead_score
  ix_seller_leads_priority_level
  ix_seller_leads_outreach_status
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("seller_leads", sa.Column("lead_score",           sa.Numeric(5, 2),   nullable=True))
    op.add_column("seller_leads", sa.Column("score_breakdown_json", sa.Text(),          nullable=True))
    op.add_column("seller_leads", sa.Column("priority_level",       sa.String(20),      nullable=True))
    op.add_column("seller_leads", sa.Column("reviewed_at",          sa.DateTime(),      nullable=True))
    op.add_column("seller_leads", sa.Column("reviewed_by",          sa.String(100),     nullable=True))
    op.add_column("seller_leads", sa.Column("outreach_status",      sa.String(30),      nullable=True, server_default="pending"))
    op.add_column("seller_leads", sa.Column("outreach_notes",       sa.Text(),          nullable=True))

    op.create_index("ix_seller_leads_lead_score",      "seller_leads", ["lead_score"])
    op.create_index("ix_seller_leads_priority_level",  "seller_leads", ["priority_level"])
    op.create_index("ix_seller_leads_outreach_status", "seller_leads", ["outreach_status"])


def downgrade() -> None:
    op.drop_index("ix_seller_leads_outreach_status", table_name="seller_leads")
    op.drop_index("ix_seller_leads_priority_level",  table_name="seller_leads")
    op.drop_index("ix_seller_leads_lead_score",      table_name="seller_leads")

    op.drop_column("seller_leads", "outreach_notes")
    op.drop_column("seller_leads", "outreach_status")
    op.drop_column("seller_leads", "reviewed_by")
    op.drop_column("seller_leads", "reviewed_at")
    op.drop_column("seller_leads", "priority_level")
    op.drop_column("seller_leads", "score_breakdown_json")
    op.drop_column("seller_leads", "lead_score")
