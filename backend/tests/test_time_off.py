import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user

START_DATE = "2026-06-10"
END_DATE = "2026-06-12"


@pytest.fixture
def employee_in_org(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    employee = add_employee_member(client, org_id, auth_headers)
    yield employee
    cleanup_user(db, employee["user_id"])


def _create_request(
    client: TestClient,
    org_id: str,
    headers: dict[str, str],
    *,
    start_date: str = START_DATE,
    end_date: str = END_DATE,
    reason: str = "Vacation",
) -> dict:
    response = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=headers,
        json={"start_date": start_date, "end_date": end_date, "reason": reason},
    )
    assert response.status_code == 201
    return response.json()


def test_employee_creates_time_off_request(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    data = _create_request(client, org_id, employee_in_org["headers"])
    assert data["status"] == "PENDING"
    assert data["employee_id"] == employee_in_org["user_id"]
    assert data["reason"] == "Vacation"


def test_employee_lists_own_time_off_requests(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    _create_request(client, org_id, employee_in_org["headers"])

    response = client.get(
        f"/organizations/{org_id}/time-off-requests/me",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_manager_lists_pending_time_off_requests(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    _create_request(client, org_id, employee_in_org["headers"])

    response = client.get(
        f"/organizations/{org_id}/time-off-requests",
        headers=auth_headers,
        params={"status": "PENDING"},
    )
    assert response.status_code == 200
    pending = response.json()
    assert len(pending) >= 1
    assert all(item["status"] == "PENDING" for item in pending)


def test_manager_approves_time_off_request(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    request_id = _create_request(client, org_id, employee_in_org["headers"])["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["reviewed_by_id"] is not None


def test_manager_rejects_time_off_request(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    request_id = _create_request(client, org_id, employee_in_org["headers"])["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/reject",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_employee_cancels_pending_time_off_request(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    request_id = _create_request(client, org_id, employee_in_org["headers"])["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/cancel",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_employee_cannot_approve_time_off_request(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    request_id = _create_request(client, org_id, employee_in_org["headers"])["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403


def test_employee_cannot_list_org_time_off_queue(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.get(
        f"/organizations/{org_id}/time-off-requests",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403


def test_cannot_approve_non_pending_request(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    request_id = _create_request(client, org_id, employee_in_org["headers"])["id"]
    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 400
