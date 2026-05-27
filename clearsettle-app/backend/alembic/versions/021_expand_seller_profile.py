"""Expand company and user tables for public seller onboarding.

Revision ID: 021
Revises: 020
Create Date: 2026-05-22

Adds:
  users.phone                   — mobile number for login / OTP
  companies.phone               — contact phone
  companies.pan                 — PAN card number (optional)
  companies.state               — state name
  companies.state_code          — 2-digit GSTIN state code
  companies.pincode             — PIN code
  companies.address             — full address
  companies.website             — business website
  companies.active_platforms    — JSONB array of marketplace slugs
  companies.bank_name           — bank name
  companies.bank_account_number — account number
  companies.bank_ifsc           — IFSC code
  companies.bank_account_name   — account holder name
  companies.monthly_gmv_range   — self-declared GMV bucket
  companies.registration_completed — True once public registration done
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))
    op.create_index("ix_users_phone", "users", ["phone"])

    # ── companies ─────────────────────────────────────────────────────────────
    op.add_column("companies", sa.Column("phone",                sa.String(20),  nullable=True))
    op.add_column("companies", sa.Column("pan",                  sa.String(15),  nullable=True))
    op.add_column("companies", sa.Column("state",                sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("state_code",           sa.String(5),   nullable=True))
    op.add_column("companies", sa.Column("pincode",              sa.String(10),  nullable=True))
    op.add_column("companies", sa.Column("address",              sa.Text,        nullable=True))
    op.add_column("companies", sa.Column("website",              sa.String(255), nullable=True))
    op.add_column("companies", sa.Column(
        "active_platforms",
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=True,
    ))
    op.add_column("companies", sa.Column("bank_name",            sa.String(100), nullable=True))
    op.add_column("companies", sa.Column("bank_account_number",  sa.String(50),  nullable=True))
    op.add_column("companies", sa.Column("bank_ifsc",            sa.String(20),  nullable=True))
    op.add_column("companies", sa.Column("bank_account_name",    sa.String(255), nullable=True))
    op.add_column("companies", sa.Column("monthly_gmv_range",    sa.String(50),  nullable=True))
    op.add_column("companies", sa.Column(
        "registration_completed",
        sa.Boolean,
        nullable=False,
        server_default="false",
    ))


def downgrade() -> None:
    op.drop_column("companies", "registration_completed")
    op.drop_column("companies", "monthly_gmv_range")
    op.drop_column("companies", "bank_account_name")
    op.drop_column("companies", "bank_ifsc")
    op.drop_column("companies", "bank_account_number")
    op.drop_column("companies", "bank_name")
    op.drop_column("companies", "active_platforms")
    op.drop_column("companies", "website")
    op.drop_column("companies", "address")
    op.drop_column("companies", "pincode")
    op.drop_column("companies", "state_code")
    op.drop_column("companies", "state")
    op.drop_column("companies", "pan")
    op.drop_column("companies", "phone")
    op.drop_index("ix_users_phone", "users")
    op.drop_column("users", "phone")
