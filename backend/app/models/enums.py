import enum


class MembershipRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class ShiftStatus(str, enum.Enum):
    DRAFT = "DRAFT"


class TimeOffStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
