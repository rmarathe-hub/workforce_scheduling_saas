"""add employee documents

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    document_type = postgresql.ENUM(
        "TRAINING_CERTIFICATE",
        "FOOD_SAFETY_CERTIFICATE",
        "CPR_CERTIFICATE",
        "SIGNED_EMPLOYMENT_FORM",
        "ID_WORK_AUTHORIZATION",
        name="document_type",
        create_type=False,
    )
    document_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "employee_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=False),
        sa.Column("document_type", document_type, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("s3_key", name="uq_employee_documents_s3_key"),
    )
    op.create_index(
        "ix_employee_documents_org_employee",
        "employee_documents",
        ["organization_id", "employee_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_employee_documents_org_employee", table_name="employee_documents")
    op.drop_table("employee_documents")
    postgresql.ENUM(name="document_type").drop(op.get_bind(), checkfirst=True)
