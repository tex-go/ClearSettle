"""Cash flow snapshots + meeting system.

Revision ID: 019
Revises: 018
Create Date: 2026-05-19

Creates:
  cash_flow_snapshots  — daily/weekly/monthly/quarterly aggregated cash flow
  meetings             — scheduled meetings (Teams / Zoom / in-person)
  meeting_participants — per-person RSVP records
  meeting_notes        — pre-meeting / action items / decisions
  meeting_reminders    — scheduled reminder jobs (email / WhatsApp / in-app)
  meeting_status_history — immutable status change audit
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision      = '019'
down_revision = '018'
branch_labels = None
depends_on    = None


def upgrade():
    # ── cash_flow_snapshots ───────────────────────────────────────────────────
    op.create_table(
        'cash_flow_snapshots',
        sa.Column('id',            UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id',    UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('snapshot_date', sa.Date(),        nullable=False),
        sa.Column('period_type',   sa.String(20),    nullable=False),  # daily/weekly/monthly/quarterly
        sa.Column('opening_balance',      sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('inflows',              sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('outflows',             sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('net_cash_flow',        sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('closing_balance',      sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('settlements_count',    sa.Integer(),      nullable=False, server_default='0'),
        sa.Column('fees_total',           sa.Numeric(18, 4), nullable=False, server_default='0'),
        sa.Column('platform_breakdown_json', JSONB(),        nullable=True),
        sa.Column('currency',             sa.String(10),     nullable=False, server_default="'INR'"),
        sa.Column('ai_insights_json',     JSONB(),           nullable=True),
        sa.Column('ai_shortage_risk',     sa.String(20),     nullable=True),   # low/medium/high/critical
        sa.Column('ai_generated_at',      sa.DateTime(),     nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_cfs_company_date_type', 'cash_flow_snapshots',
                    ['company_id', 'snapshot_date', 'period_type'])
    op.create_unique_constraint('uq_cfs_company_date_type', 'cash_flow_snapshots',
                                ['company_id', 'snapshot_date', 'period_type'])

    # ── meetings ──────────────────────────────────────────────────────────────
    op.create_table(
        'meetings',
        sa.Column('id',         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('company_id', UUID(as_uuid=True),
                  sa.ForeignKey('companies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_meeting_id', UUID(as_uuid=True),
                  sa.ForeignKey('meetings.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title',        sa.String(255), nullable=False),
        sa.Column('description',  sa.Text(),      nullable=True),
        sa.Column('meeting_type', sa.String(50),  nullable=False, server_default="'internal'"),
        # internal / external / client / vendor / team
        sa.Column('status', sa.String(50), nullable=False, server_default="'scheduled'"),
        # scheduled / confirmed / cancelled / completed / rescheduled
        sa.Column('start_at',  sa.DateTime(), nullable=False),
        sa.Column('end_at',    sa.DateTime(), nullable=False),
        sa.Column('timezone',  sa.String(50),  nullable=False, server_default="'Asia/Kolkata'"),
        sa.Column('location',  sa.String(500), nullable=True),
        sa.Column('platform',  sa.String(50),  nullable=True),  # teams/zoom/meet/in_person
        sa.Column('platform_meeting_url', sa.String(1000), nullable=True),
        sa.Column('platform_meeting_id',  sa.String(255),  nullable=True),
        sa.Column('organizer_email', sa.String(255), nullable=False),
        sa.Column('organizer_name',  sa.String(255), nullable=True),
        sa.Column('agenda',          sa.Text(),      nullable=True),
        sa.Column('recurrence_rule', sa.String(500), nullable=True),  # iCal RRULE
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_meetings_company_start', 'meetings', ['company_id', 'start_at'])
    op.create_index('idx_meetings_status',        'meetings', ['status'])

    # ── meeting_participants ──────────────────────────────────────────────────
    op.create_table(
        'meeting_participants',
        sa.Column('id',         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('meeting_id', UUID(as_uuid=True),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name',  sa.String(255), nullable=True),
        sa.Column('role',  sa.String(50),  nullable=False, server_default="'required'"),
        # organizer / required / optional
        sa.Column('rsvp_status',  sa.String(50),  nullable=False, server_default="'pending'"),
        # pending / accepted / declined / tentative
        sa.Column('responded_at', sa.DateTime(), nullable=True),
        sa.Column('notes',        sa.Text(),     nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_mp_meeting_id',    'meeting_participants', ['meeting_id'])
    op.create_index('idx_mp_email_meeting', 'meeting_participants', ['email', 'meeting_id'])
    op.create_unique_constraint('uq_meeting_participant', 'meeting_participants',
                                ['meeting_id', 'email'])

    # ── meeting_notes ─────────────────────────────────────────────────────────
    op.create_table(
        'meeting_notes',
        sa.Column('id',         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('meeting_id', UUID(as_uuid=True),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('note_type',  sa.String(50), nullable=False, server_default="'general'"),
        # pre_meeting / action_item / decision / general / follow_up
        sa.Column('content',    sa.Text(),     nullable=False),
        sa.Column('created_by', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_mn_meeting_id', 'meeting_notes', ['meeting_id'])

    # ── meeting_reminders ─────────────────────────────────────────────────────
    op.create_table(
        'meeting_reminders',
        sa.Column('id',         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('meeting_id', UUID(as_uuid=True),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('participant_email', sa.String(255), nullable=True),  # null = all participants
        sa.Column('reminder_type',  sa.String(50),  nullable=False),  # email/whatsapp/in_app
        sa.Column('minutes_before', sa.Integer(),   nullable=False),  # 15, 60, 1440
        sa.Column('scheduled_at',   sa.DateTime(),  nullable=False),
        sa.Column('sent_at',        sa.DateTime(),  nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default="'pending'"),
        # pending / sent / failed / skipped
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_mr_meeting_id',    'meeting_reminders', ['meeting_id'])
    op.create_index('idx_mr_scheduled_at',  'meeting_reminders', ['scheduled_at'])
    op.create_index('idx_mr_status_sched',  'meeting_reminders', ['status', 'scheduled_at'])

    # ── meeting_status_history ────────────────────────────────────────────────
    op.create_table(
        'meeting_status_history',
        sa.Column('id',         UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('meeting_id', UUID(as_uuid=True),
                  sa.ForeignKey('meetings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('old_status', sa.String(50), nullable=True),
        sa.Column('new_status', sa.String(50), nullable=False),
        sa.Column('changed_by', sa.String(255), nullable=False),
        sa.Column('reason',     sa.Text(),      nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('idx_msh_meeting_id', 'meeting_status_history', ['meeting_id'])


def downgrade():
    op.drop_table('meeting_status_history')
    op.drop_table('meeting_reminders')
    op.drop_table('meeting_notes')
    op.drop_table('meeting_participants')
    op.drop_table('meetings')
    op.drop_index('idx_cfs_company_date_type', table_name='cash_flow_snapshots')
    op.drop_constraint('uq_cfs_company_date_type', 'cash_flow_snapshots', type_='unique')
    op.drop_table('cash_flow_snapshots')
