"""Extended time-off validation and RBAC tests."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user

START_DATE = "2026-06-10"
END_DATE = "2026-06-12"

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture
def employee_in_org(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    employee = add_employee_member(client, org_id, auth_headers)
    yield employee
    cleanup_user(db, employee["user_id"])


def test_employee_cannot_cancel_other_employee_time_off(
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
    request_id = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=other["headers"],
        json={"start_date": START_DATE, "end_date": END_DATE, "reason": "Away"},
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/cancel",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, other["user_id"])


def test_employee_cannot_approve_own_time_off(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    request_id = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=employee_in_org["headers"],
        json={"start_date": START_DATE, "end_date": END_DATE, "reason": "Away"},
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=employee_in_org["headers"],
    )
    assert response.status_code == 403


def test_reject_already_approved_request_returns_400(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_in_org: dict[str, str],
) -> None:
    request_id = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=employee_in_org["headers"],
        json={"start_date": START_DATE, "end_date": END_DATE, "reason": "Away"},
    ).json()["id"]
    client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=auth_headers,
    )

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/reject",
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_time_off_invalid_date_range_returns_400(
    client: TestClient, org_id: str, employee_in_org: dict[str, str]
) -> None:
    response = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=employee_in_org["headers"],
        json={"start_date": END_DATE, "end_date": START_DATE, "reason": "Bad range"},
    )
    assert response.status_code == 422
