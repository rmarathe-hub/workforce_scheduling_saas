"""Placeholder tests for future schedule generator module."""

import pytest

pytestmark = pytest.mark.future


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
