"""add published and cancelled shift statuses

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE shift_status ADD VALUE IF NOT EXISTS 'PUBLISHED'")
    op.execute("ALTER TYPE shift_status ADD VALUE IF NOT EXISTS 'CANCELLED'")


def downgrade() -> None:
    pass
