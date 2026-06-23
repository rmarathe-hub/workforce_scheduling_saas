"""Extended conflict API tests for additional conflict types."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.shift import Shift
from tests.helpers import cleanup_user
from tests.test_scheduling import WEEK_START, _setup_org_scheduling

SHIFT_DATE = "2026-06-02"


def test_get_conflicts_detects_role_mismatch(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    cook_role_id = client.post(
        f"/organizations/{org_id}/job-roles",
        headers=auth_headers,
        json={"name": "Cook"},
    ).json()["id"]

    shift_id = client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": cook_role_id,
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    ).json()["id"]

    shift = db.get(Shift, uuid.UUID(shift_id))
    assert shift is not None
    shift.assignee_id = uuid.UUID(setup["employee_user_id"])
    db.commit()

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(conflict["type"] == "ROLE_MISMATCH" for conflict in response.json()["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_get_conflicts_detects_max_hours_warning(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)

    for day_offset, start, end in (
        (0, "08:00:00", "16:00:00"),
        (1, "08:00:00", "16:00:00"),
        (2, "08:00:00", "16:00:00"),
        (3, "08:00:00", "16:00:00"),
        (4, "08:00:00", "16:00:00"),
        (5, "08:00:00", "12:00:00"),
    ):
        shift_date = f"2026-06-{2 + day_offset:02d}"
        shift_id = client.post(
            f"/organizations/{org_id}/shifts",
            headers=auth_headers,
            json={
                "location_id": setup["location_id"],
                "job_role_id": setup["job_role_id"],
                "shift_date": shift_date,
                "start_time": start,
                "end_time": end,
            },
        ).json()["id"]
        client.patch(
            f"/organizations/{org_id}/shifts/{shift_id}/assign",
            headers=auth_headers,
            json={"assignee_id": setup["employee_user_id"]},
        )

    response = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}/conflicts",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert any(conflict["type"] == "MAX_HOURS" for conflict in response.json()["conflicts"])

    cleanup_user(db, setup["employee_user_id"])


def test_validate_week_returns_summary_structure(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    client.post(
        f"/organizations/{org_id}/shifts",
        headers=auth_headers,
        json={
            "location_id": setup["location_id"],
            "job_role_id": setup["job_role_id"],
            "shift_date": SHIFT_DATE,
            "start_time": "09:00:00",
            "end_time": "17:00:00",
        },
    )

    response = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/validate",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "summary" in data
    assert set(data["summary"].keys()) == {"total", "errors", "warnings", "info"}

    cleanup_user(db, setup["employee_user_id"])
