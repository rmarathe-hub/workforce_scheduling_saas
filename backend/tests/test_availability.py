import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user


@pytest.fixture
def employee_in_org(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    employee = add_employee_member(client, org_id, auth_headers)
    yield employee
    cleanup_user(db, employee["user_id"])


def test_employee_creates_availability_window(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 0, "start_time": "09:00:00", "end_time": "17:00:00"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["day_of_week"] == 0
    assert data["day_name"] == "Monday"
    assert data["employee_id"] == employee_in_org["user_id"]


def test_employee_lists_own_availability(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 1, "start_time": "10:00:00", "end_time": "18:00:00"},
    )

    response = client.get(
        f"/organizations/{org_id}/availability/me",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 200
    windows = response.json()
    assert len(windows) == 1
    assert windows[0]["day_name"] == "Tuesday"


def test_manager_views_employee_availability(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 2, "start_time": "08:00:00", "end_time": "16:00:00"},
    )

    response = client.get(
        f"/organizations/{org_id}/employees/{employee_in_org['user_id']}/availability",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["day_of_week"] == 2


def test_employee_cannot_view_other_employee_availability_via_manager_endpoint(
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

    response = client.get(
        f"/organizations/{org_id}/employees/{other['user_id']}/availability",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, other["user_id"])


def test_employee_updates_own_availability(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    window_id = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 3, "start_time": "09:00:00", "end_time": "12:00:00"},
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/availability/{window_id}",
        headers=employee_in_org["headers"],
        json={"end_time": "13:00:00"},
    )
    assert response.status_code == 200
    assert response.json()["end_time"].startswith("13:00")


def test_employee_cannot_update_other_employee_availability(
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
        json={"day_of_week": 4, "start_time": "09:00:00", "end_time": "17:00:00"},
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/availability/{window_id}",
        headers=employee_in_org["headers"],
        json={"end_time": "18:00:00"},
    )
    assert response.status_code == 403

    cleanup_user(db, other["user_id"])


def test_employee_deletes_own_availability(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    window_id = client.post(
        f"/organizations/{org_id}/availability",
        headers=employee_in_org["headers"],
        json={"day_of_week": 5, "start_time": "09:00:00", "end_time": "17:00:00"},
    ).json()["id"]

    delete_response = client.delete(
        f"/organizations/{org_id}/availability/{window_id}",
        headers=employee_in_org["headers"],
    )
    assert delete_response.status_code == 204

    list_response = client.get(
        f"/organizations/{org_id}/availability/me",
        headers=employee_in_org["headers"],
    )
    assert list_response.json() == []
