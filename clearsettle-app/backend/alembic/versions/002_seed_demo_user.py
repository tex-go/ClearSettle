"""Seed demo user + company + platform connection stubs

Revision ID: 002
Revises: 001
Create Date: 2026-05-17
"""
from typing import Sequence, Union
import uuid
from datetime import datetime

import bcrypt
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_USER_ID    = str(uuid.UUID("00000000-0000-0000-0000-000000000001"))
DEMO_COMPANY_ID = str(uuid.UUID("00000000-0000-0000-0000-000000000002"))

PLATFORMS = [
    "amazon", "flipkart", "meesho", "myntra",
    "nykaa", "ajio", "snapdeal", "jiomart",
]


def upgrade() -> None:
    hashed = bcrypt.hashpw(b"demo123", bcrypt.gensalt(rounds=10)).decode()
    now = datetime.utcnow()

    op.execute(
        sa.text("""
            INSERT INTO users (id, email, hashed_password, name, role, is_active, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, 'admin', true, :now, :now)
            ON CONFLICT (email) DO NOTHING
        """).bindparams(
            id=DEMO_USER_ID,
            email="demo@clearsettle.in",
            pw=hashed,
            name="Ranjith Kumar",
            now=now,
        )
    )

    op.execute(
        sa.text("""
            INSERT INTO companies (id, user_id, name, gstin, city, industry, created_at, updated_at)
            VALUES (:id, :uid, :name, :gstin, :city, :industry, :now, :now)
            ON CONFLICT DO NOTHING
        """).bindparams(
            id=DEMO_COMPANY_ID,
            uid=DEMO_USER_ID,
            name="Tirupur Exports Pvt. Ltd.",
            gstin="33ABCDE1234F1Z5",
            city="Tirupur, Tamil Nadu",
            industry="Textile & Apparel",
            now=now,
        )
    )

    for platform in PLATFORMS:
        op.execute(
            sa.text("""
                INSERT INTO platform_connections
                    (id, company_id, platform, status, created_at, updated_at)
                VALUES (:id, :cid, :platform, 'disconnected', :now, :now)
                ON CONFLICT (company_id, platform) DO NOTHING
            """).bindparams(
                id=str(uuid.uuid4()),
                cid=DEMO_COMPANY_ID,
                platform=platform,
                now=now,
            )
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM users WHERE id = :id").bindparams(id=DEMO_USER_ID)
    )
