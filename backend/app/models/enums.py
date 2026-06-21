import enum


class MembershipRole(str, enum.Enum):
    OWNER = "OWNER"
    MANAGER = "MANAGER"
    EMPLOYEE = "EMPLOYEE"


class ShiftStatus(str, enum.Enum):
    DRAFT = "DRAFT"
