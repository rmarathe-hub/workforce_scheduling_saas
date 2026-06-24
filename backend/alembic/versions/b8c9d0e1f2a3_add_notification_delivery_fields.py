"""add notification delivery fields

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("notifications", "retry_count")
    op.drop_column("notifications", "error_message")
