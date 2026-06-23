"""Shift swap request API tests (Week 4 Day 22)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import add_employee_member, cleanup_user
from tests.test_schedule_integration import (
    SHIFT_DATE,
    _create_coverage,
    _set_employee_availability,
)
from tests.test_scheduling import WEEK_START, _setup_org_scheduling


@pytest.fixture
def published_employee_shift(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup)

    generate = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate.status_code == 200

    publish = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert publish.status_code == 200

    my_shifts = client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=setup["employee_headers"],
        params={"week_start": WEEK_START},
    ).json()
    assert len(my_shifts) == 1
    assert my_shifts[0]["status"] == "PUBLISHED"

    yield {
        **setup,
        "shift_id": my_shifts[0]["id"],
    }

    cleanup_user(db, setup["employee_user_id"])


def _create_give_up_request(
    client: TestClient,
    org_id: str,
    headers: dict[str, str],
    shift_id: str,
    *,
    reason: str = "Cannot work",
) -> dict:
    response = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=headers,
        json={
            "request_type": "GIVE_UP",
            "original_shift_id": shift_id,
            "reason": reason,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_employee_can_request_give_up_for_own_published_shift(
    client: TestClient,
    org_id: str,
    published_employee_shift: dict[str, str],
) -> None:
    data = _create_give_up_request(
        client,
        org_id,
        published_employee_shift["employee_headers"],
        published_employee_shift["shift_id"],
    )
    assert data["status"] == "PENDING"
    assert data["request_type"] == "GIVE_UP"
    assert data["requester_id"] == published_employee_shift["employee_user_id"]


def test_employee_cannot_request_give_up_for_draft_shift(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    _create_coverage(
        client,
        org_id,
        auth_headers,
        setup,
        start_time="13:00:00",
        end_time="17:00:00",
    )
    generate = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate.status_code == 200

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()
    draft_shift = next(shift for shift in schedule["shifts"] if shift["status"] == "DRAFT")

    response = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={
            "request_type": "GIVE_UP",
            "original_shift_id": draft_shift["id"],
        },
    )
    assert response.status_code == 400


def test_manager_can_approve_give_up_and_unassigns_shift(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    request_id = _create_give_up_request(
        client, org_id, setup["employee_headers"], setup["shift_id"]
    )["id"]

    response = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/approve",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()
    shift = next(item for item in schedule["shifts"] if item["id"] == setup["shift_id"])
    assert shift["assignee_id"] is None

    my_shifts = client.get(
        f"/organizations/{org_id}/my-shifts",
        headers=setup["employee_headers"],
        params={"week_start": WEEK_START},
    ).json()
    assert my_shifts == []


def test_manager_can_reject_give_up_request(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    request_id = _create_give_up_request(
        client, org_id, setup["employee_headers"], setup["shift_id"]
    )["id"]

    response = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/reject",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_employee_cannot_approve_own_swap_request(
    client: TestClient,
    org_id: str,
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    request_id = _create_give_up_request(
        client, org_id, setup["employee_headers"], setup["shift_id"]
    )["id"]

    response = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/approve",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403


def test_manager_lists_pending_swap_requests(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    _create_give_up_request(client, org_id, setup["employee_headers"], setup["shift_id"])

    response = client.get(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=auth_headers,
        params={"status": "PENDING"},
    )
    assert response.status_code == 200
    pending = response.json()
    assert len(pending) >= 1
    assert all(item["status"] == "PENDING" for item in pending)


def test_employee_can_cancel_pending_swap_request(
    client: TestClient,
    org_id: str,
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    request_id = _create_give_up_request(
        client, org_id, setup["employee_headers"], setup["shift_id"]
    )["id"]

    response = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/cancel",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
