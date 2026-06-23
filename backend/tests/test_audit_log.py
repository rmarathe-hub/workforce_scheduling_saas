"""Audit log API tests (Week 4 Day 23)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user, register_user_with_org
from tests.test_schedule_integration import _create_coverage, _set_employee_availability
from tests.test_scheduling import WEEK_START, _setup_org_scheduling
from tests.test_shift_swap import _create_give_up_request, published_employee_shift  # noqa: F401


def test_shift_swap_request_creates_audit_log(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    _create_give_up_request(client, org_id, setup["employee_headers"], setup["shift_id"])

    response = client.get(
        f"/organizations/{org_id}/audit-logs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    actions = [item["action"] for item in data["items"]]
    assert "SHIFT_SWAP_REQUESTED" in actions


def test_shift_swap_approval_creates_audit_log(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    request_id = _create_give_up_request(
        client, org_id, setup["employee_headers"], setup["shift_id"]
    )["id"]

    client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{request_id}/approve",
        headers=auth_headers,
    ).raise_for_status()

    response = client.get(f"/organizations/{org_id}/audit-logs", headers=auth_headers)
    actions = [item["action"] for item in response.json()["items"]]
    assert "SHIFT_SWAP_APPROVED" in actions


def test_schedule_generate_and_publish_create_audit_logs(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])
    _create_coverage(client, org_id, auth_headers, setup)

    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    ).raise_for_status()
    client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    ).raise_for_status()

    response = client.get(f"/organizations/{org_id}/audit-logs", headers=auth_headers)
    actions = [item["action"] for item in response.json()["items"]]
    assert "SCHEDULE_GENERATED" in actions
    assert "SCHEDULE_PUBLISHED" in actions

    cleanup_user(db, setup["employee_user_id"])


def test_employee_cannot_view_audit_logs(
    client: TestClient,
    org_id: str,
    published_employee_shift: dict[str, str],
) -> None:
    setup = published_employee_shift
    response = client.get(
        f"/organizations/{org_id}/audit-logs",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403


def test_cross_org_cannot_view_audit_logs(
    client: TestClient,
    db: Session,
    org_id: str,
    published_employee_shift: dict[str, str],
) -> None:
    org_b = register_user_with_org(client)
    _create_give_up_request(
        client,
        org_id,
        published_employee_shift["employee_headers"],
        published_employee_shift["shift_id"],
    )

    response = client.get(
        f"/organizations/{org_id}/audit-logs",
        headers=org_b["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, org_b["user_id"])
