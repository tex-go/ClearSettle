"""Add file_hash to flipkart_reports for deduplication."""
from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "flipkart_reports",
        sa.Column("file_hash", sa.String(64), nullable=True, index=True),
    )


def downgrade():
    op.drop_column("flipkart_reports", "file_hash")
