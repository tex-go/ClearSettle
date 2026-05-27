"""Fix flipkart_reports status VARCHAR(20) → VARCHAR(50); ensure file_hash is VARCHAR(64)."""
from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "flipkart_reports", "status",
        existing_type=sa.String(20),
        type_=sa.String(50),
        existing_nullable=False,
    )
    op.alter_column(
        "flipkart_reports", "file_hash",
        existing_type=sa.String(),
        type_=sa.String(64),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "flipkart_reports", "file_hash",
        existing_type=sa.String(64),
        type_=sa.String(),
        existing_nullable=True,
    )
    op.alter_column(
        "flipkart_reports", "status",
        existing_type=sa.String(50),
        type_=sa.String(20),
        existing_nullable=False,
    )
