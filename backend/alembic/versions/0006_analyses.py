"""Add analyses table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-31

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analyses",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("assessment", sa.String(length=30), nullable=False),
        sa.Column("risk_level", sa.String(length=20), server_default="Moderate", nullable=False),
        sa.Column("market_price", sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column("timeframe", sa.String(length=10), server_default="1D", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("key_price_levels", sa.JSON(), nullable=True),
        sa.Column("technical_indicators", sa.JSON(), nullable=True),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_analyses_user_id"), "analyses", ["user_id"], unique=False
    )
    op.create_index(
        "ix_analyses_user_id_symbol", "analyses", ["user_id", "symbol"], unique=False
    )
    op.create_index(
        "ix_analyses_user_id_created_at", "analyses", ["user_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_analyses_user_id_created_at", table_name="analyses")
    op.drop_index("ix_analyses_user_id_symbol", table_name="analyses")
    op.drop_index(op.f("ix_analyses_user_id"), table_name="analyses")
    op.drop_table("analyses")
