"""Placeholder tests for Week 2+ scheduling engine modules."""

import pytest

pytestmark = pytest.mark.future


@pytest.mark.parametrize(
    "rule",
    [
        "overlapping shifts",
        "employee unavailable",
        "wrong role",
        "approved time off conflict",
        "max weekly hours",
        "open/unfilled shift",
    ],
)
def test_conflict_detector_rules_not_implemented_yet(rule: str) -> None:
    pytest.skip(f"conflict_detector.py not implemented yet ({rule})")


@pytest.mark.parametrize(
    "behavior",
    [
        "assigns eligible employee",
        "skips unavailable employee",
        "balances hours where possible",
        "leaves shift open when no eligible employee exists",
    ],
)
def test_schedule_generator_behaviors_not_implemented_yet(behavior: str) -> None:
    pytest.skip(f"schedule_generator.py not implemented yet ({behavior})")
