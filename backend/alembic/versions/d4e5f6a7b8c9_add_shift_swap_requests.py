"""add shift swap requests

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    shift_swap_request_type = postgresql.ENUM(
        "GIVE_UP",
        "SWAP",
        name="shift_swap_request_type",
        create_type=False,
    )
    shift_swap_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        name="shift_swap_status",
        create_type=False,
    )
    shift_swap_request_type.create(op.get_bind(), checkfirst=True)
    shift_swap_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shift_swap_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("requester_id", sa.UUID(), nullable=False),
        sa.Column("target_employee_id", sa.UUID(), nullable=True),
        sa.Column("original_shift_id", sa.UUID(), nullable=False),
        sa.Column("requested_shift_id", sa.UUID(), nullable=True),
        sa.Column("request_type", shift_swap_request_type, nullable=False),
        sa.Column("status", shift_swap_status, nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("decided_by_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_shift_id"], ["shifts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_shift_id"], ["shifts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requester_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_employee_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("shift_swap_requests")
    postgresql.ENUM(name="shift_swap_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="shift_swap_request_type").drop(op.get_bind(), checkfirst=True)
