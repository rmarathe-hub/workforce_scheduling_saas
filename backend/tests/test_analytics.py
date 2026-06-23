"""Manager dashboard analytics API tests (Week 4 Day 26)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user, register_user_with_org
from tests.test_scheduling import _setup_org_scheduling

WEEK_START = "2026-06-01"
SHIFT_DATE = "2026-06-02"


def _create_coverage_and_shift(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    setup: dict[str, str],
    *,
    assign: bool = True,
    publish: bool = False,
) -> str:
    requirement_id = client.post(
        f"/organizations/{org_id}/coverage-requirements",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "week_start": WEEK_START,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "headcount": 2,
        },
    ).json()["id"]

    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
            "coverage_requirement_id": requirement_id,
        },
    ).json()["id"]

    if assign:
        client.patch(
            f"/organizations/{org_id}/shifts/{shift_id}/assign",
            headers=auth_headers,
            json={"assignee_id": setup["employee_user_id"]},
        )

    if publish:
        client.post(
            f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
            headers=auth_headers,
        )

    return shift_id


def test_manager_dashboard_returns_metrics(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _create_coverage_and_shift(client, org_id, auth_headers, setup, assign=True, publish=True)

    client.post(
        f"/organizations/{org_id}/time-off-requests",
        headers=setup["employee_headers"],
        json={"start_date": "2026-06-10", "end_date": "2026-06-11", "reason": "Trip"},
    )

    response = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["week_start"] == WEEK_START
    assert data["total_employees"] >= 1
    assert data["published_shifts"] >= 1
    assert data["pending_time_off"] >= 1
    assert data["scheduled_hours"] == 8.0
    assert 0 <= data["coverage_fill_rate"] <= 100
    assert data["conflict_count"] >= 0


def test_dashboard_reflects_open_shifts(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _create_coverage_and_shift(client, org_id, auth_headers, setup, assign=False)

    response = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["open_shifts"] >= 1
    assert data["coverage_fill_rate"] == 0.0


def test_dashboard_reflects_partial_coverage_fill_rate(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _create_coverage_and_shift(client, org_id, auth_headers, setup, assign=True)

    response = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["coverage_fill_rate"] == 50.0


def test_employee_cannot_access_dashboard(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    response = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403


def test_cross_org_cannot_access_dashboard(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    other_org = register_user_with_org(client)

    response = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=other_org["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, other_org["user_id"])
