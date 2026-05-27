"""Add report_type to flipkart_reports."""
from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "flipkart_reports",
        sa.Column(
            "report_type",
            sa.String(30),
            nullable=False,
            server_default="pl_report",
        ),
    )


def downgrade():
    op.drop_column("flipkart_reports", "report_type")
