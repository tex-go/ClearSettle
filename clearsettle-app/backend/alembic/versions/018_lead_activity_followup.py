"""Lead activity audit log + follow-up scheduling.

Revision ID: 018
Revises: 017
Create Date: 2026-05-19

Adds:
  seller_leads.follow_up_at   TIMESTAMP  — next scheduled follow-up
  seller_leads.assigned_to    VARCHAR    — team member owning this lead

Creates:
  seller_lead_activity        — immutable per-entry audit log
    (note | follow_up | call_log | email_log | whatsapp_log |
     tag | status_change | classify | score | outreach)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision    = '018'
down_revision = '017'
branch_labels = None
depends_on    = None


def upgrade():
    op.add_column('seller_leads', sa.Column('follow_up_at', sa.DateTime(), nullable=True))
    op.add_column('seller_leads', sa.Column('assigned_to',  sa.String(100), nullable=True))

    op.create_table(
        'seller_lead_activity',
        sa.Column('id',            UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('lead_id',       UUID(as_uuid=True),
                  sa.ForeignKey('seller_leads.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_type', sa.String(50),  nullable=False),
        sa.Column('content',       sa.Text(),       nullable=True),
        sa.Column('metadata_json', JSONB(),         nullable=True),
        sa.Column('created_by',    sa.String(100),  nullable=False),
        sa.Column('created_at',    sa.DateTime(),   nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index(
        'idx_lead_activity_lead_created',
        'seller_lead_activity',
        ['lead_id', 'created_at'],
    )


def downgrade():
    op.drop_index('idx_lead_activity_lead_created', table_name='seller_lead_activity')
    op.drop_table('seller_lead_activity')
    op.drop_column('seller_leads', 'assigned_to')
    op.drop_column('seller_leads', 'follow_up_at')
