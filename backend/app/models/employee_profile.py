import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Table, Column, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

employee_role_assignments = Table(
    "employee_role_assignments",
    Base.metadata,
    Column(
        "employee_profile_id",
        UUID(as_uuid=True),
        ForeignKey("employee_profiles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "job_role_id",
        UUID(as_uuid=True),
        ForeignKey("job_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_employee_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="SET NULL"), nullable=True
    )
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization: Mapped["Organization"] = relationship(back_populates="employee_profiles")
    user: Mapped["User"] = relationship(back_populates="employee_profiles")
    location: Mapped["Location | None"] = relationship(back_populates="employee_profiles")
    job_roles: Mapped[list["JobRole"]] = relationship(
        secondary=employee_role_assignments,
        back_populates="employee_profiles",
    )
