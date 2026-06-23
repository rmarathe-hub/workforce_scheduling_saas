"""Extended availability validation tests."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture
def employee_in_org(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    employee = add_employee_member(client, org_id, auth_headers)
    yield employee
    cleanup_user(db, employee["user_id"])


def test_create_availability_invalid_time_range_returns_400(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 1, "start_time": "17:00:00", "end_time": "09:00:00"},
    )
    assert response.status_code == 422


def test_create_availability_invalid_day_of_week_returns_422(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 9, "start_time": "09:00:00", "end_time": "17:00:00"},
    )
    assert response.status_code == 422


def test_employee_cannot_delete_other_employee_availability(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    other = add_employee_member(
        client,
        org_id,
        auth_headers,
        email=f"other-{uuid.uuid4()}@example.com",
    )
    window_id = client.post(
        f"/organizations/{org_id}/availability",
        headers=other["headers"],
        json={"day_of_week": 2, "start_time": "09:00:00", "end_time": "17:00:00"},
    ).json()["id"]

    response = client.delete(
        f"/organizations/{org_id}/availability/{window_id}",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, other["user_id"])
