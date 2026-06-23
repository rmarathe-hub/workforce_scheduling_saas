import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ShiftSwapRequestType, ShiftSwapStatus


class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    original_shift_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False
    )
    requested_shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True
    )
    request_type: Mapped[ShiftSwapRequestType] = mapped_column(
        Enum(ShiftSwapRequestType, name="shift_swap_request_type"),
        nullable=False,
    )
    status: Mapped[ShiftSwapStatus] = mapped_column(
        Enum(ShiftSwapStatus, name="shift_swap_status"),
        nullable=False,
        default=ShiftSwapStatus.PENDING,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    organization: Mapped["Organization"] = relationship(back_populates="shift_swap_requests")
    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])
    target_employee: Mapped["User | None"] = relationship(foreign_keys=[target_employee_id])
    decided_by: Mapped["User | None"] = relationship(foreign_keys=[decided_by_id])
    original_shift: Mapped["Shift"] = relationship(foreign_keys=[original_shift_id])
    requested_shift: Mapped["Shift | None"] = relationship(foreign_keys=[requested_shift_id])
