"""Cross-organization isolation tests."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user, register_user_with_org
from tests.test_scheduling import WEEK_START, SHIFT_DATE, _setup_org_scheduling

pytestmark = pytest.mark.usefixtures("db")


@pytest.fixture
def org_b(client: TestClient, db: Session) -> dict[str, str]:
    org = register_user_with_org(client)
    yield org
    cleanup_user(db, org["user_id"])


def test_org_b_cannot_generate_org_a_schedule(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=org_b["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, setup["employee_user_id"])


def test_org_b_cannot_publish_org_a_schedule(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=org_b["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, setup["employee_user_id"])


def test_org_b_cannot_read_org_a_conflicts(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=org_b["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, setup["employee_user_id"])


def test_org_b_cannot_assign_org_a_shift(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/shifts/{shift_id}/assign",
        headers=org_b["headers"],
        json={"assignee_id": setup["employee_user_id"]},
    )
    assert response.status_code == 403
    cleanup_user(db, setup["employee_user_id"])


def test_foreign_location_id_on_coverage_returns_404(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    foreign_location_id = client.post(
        f"/organizations/{org_b['org_id']}/locations",
        headers=org_b["headers"],
        json={"name": "Foreign"},
    ).json()["id"]
    role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cashier"},
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": foreign_location_id,
            "job_role_id": role_id,
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 1,
        },
    )
    assert response.status_code == 404


def test_foreign_shift_id_validate_returns_404(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    setup_b = _setup_org_scheduling(client, org_b["org_id"], org_b["headers"])
    shift_id = client.post(
        f"/organizations/{org_b['org_id']}/shifts",
        headers=org_b["headers"],
        json={
            "location_id": setup_b["location_id"],
            "job_role_id": setup_b["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    response = client.post(
        f"/organizations/{org_id}/shifts/{shift_id}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 404
    cleanup_user(db, setup_b["employee_user_id"])


def test_org_b_cannot_approve_org_a_time_off(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
    org_b: dict[str, str],
) -> None:
    employee = add_employee_member(client, org_id, auth_headers)
    request_id = client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=employee["headers"],
        json={"start_date": SHIFT_DATE, "end_date": SHIFT_DATE, "reason": "Away"},
    ).json()["id"]

    response = client.patch(
        f"/organizations/{org_id}/time-off-requests/{request_id}/approve",
        headers=org_b["headers"],
    )
    assert response.status_code == 403
    cleanup_user(db, employee["user_id"])
