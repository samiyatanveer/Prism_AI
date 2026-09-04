"""add user risk profile

Revision ID: 0008_user_risk_profile
Revises: 0007
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_user_risk_profile"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("risk_profile", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "risk_profile")
