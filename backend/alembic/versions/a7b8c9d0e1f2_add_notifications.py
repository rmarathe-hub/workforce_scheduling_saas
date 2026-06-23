"""add notifications

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    notification_type = postgresql.ENUM(
        "SCHEDULE_PUBLISHED",
        "TIME_OFF_APPROVED",
        "TIME_OFF_REJECTED",
        "SHIFT_SWAP_REQUESTED",
        "SHIFT_SWAP_APPROVED",
        "SHIFT_SWAP_REJECTED",
        "DOCUMENT_UPLOADED",
        "OPEN_SHIFT_CREATED",
        name="notification_type",
        create_type=False,
    )
    notification_status = postgresql.ENUM(
        "PENDING",
        "SENT",
        "FAILED",
        "READ",
        name="notification_status",
        create_type=False,
    )
    notification_channel = postgresql.ENUM(
        "IN_APP",
        "EMAIL",
        name="notification_channel",
        create_type=False,
    )
    notification_type.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)
    notification_channel.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("recipient_user_id", sa.UUID(), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_notifications_recipient_org_created",
        "notifications",
        ["organization_id", "recipient_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_org_created", table_name="notifications")
    op.drop_table("notifications")
    postgresql.ENUM(name="notification_channel").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notification_type").drop(op.get_bind(), checkfirst=True)
