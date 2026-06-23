"""Week 4 end-to-end API integration: swaps, audit, documents, analytics (Day 27)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_documents import _upload_document
from tests.test_schedule_integration import (
    WEEK_START,
    _create_coverage,
    _set_employee_availability,
)
from tests.test_scheduling import _setup_org_scheduling

pytestmark = pytest.mark.usefixtures("mock_s3")


def test_week4_workflow_publish_swap_audit_document_analytics(
    client: TestClient,
    db: Session,
    org_id: str,
    auth_headers: dict[str, str],
) -> None:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    _set_employee_availability(client, org_id, setup["employee_headers"])

    _create_coverage(client, org_id, auth_headers, setup, headcount=1)

    generate = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/generate",
        headers=auth_headers,
    )
    assert generate.status_code == 200, generate.text

    publish = client.post(
        f"/organizations/{org_id}/schedules/{WEEK_START}/publish",
        headers=auth_headers,
    )
    assert publish.status_code == 200, publish.text

    schedule = client.get(
        f"/organizations/{org_id}/schedules/{WEEK_START}",
        headers=auth_headers,
    ).json()
    published_shift_id = next(
        shift["id"] for shift in schedule["shifts"] if shift["status"] == "PUBLISHED"
    )

    swap_create = client.post(
        f"/organizations/{org_id}/shift-swap-requests",
        headers=setup["employee_headers"],
        json={
            "request_type": "GIVE_UP",
            "original_shift_id": published_shift_id,
            "reason": "Cannot work",
        },
    )
    assert swap_create.status_code == 201, swap_create.text
    swap_id = swap_create.json()["id"]

    analytics_pending = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=auth_headers,
    )
    assert analytics_pending.status_code == 200
    assert analytics_pending.json()["pending_shift_swaps"] >= 1

    approve = client.patch(
        f"/organizations/{org_id}/shift-swap-requests/{swap_id}/approve",
        headers=auth_headers,
    )
    assert approve.status_code == 200, approve.text

    audit = client.get(
        f"/organizations/{org_id}/audit-logs",
        headers=auth_headers,
    )
    assert audit.status_code == 200
    actions = {entry["action"] for entry in audit.json()["items"]}
    assert "SHIFT_SWAP_REQUESTED" in actions
    assert "SHIFT_SWAP_APPROVED" in actions
    assert "SCHEDULE_PUBLISHED" in actions

    document = _upload_document(
        client,
        org_id,
        setup["employee_headers"],
        setup["employee_user_id"],
        file_name="week4-cert.pdf",
    )
    assert document["file_name"] == "week4-cert.pdf"

    manager_docs = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=auth_headers,
    )
    assert manager_docs.status_code == 200
    assert len(manager_docs.json()) == 1

    analytics = client.get(
        f"/organizations/{org_id}/analytics/dashboard?week_start={WEEK_START}",
        headers=auth_headers,
    )
    assert analytics.status_code == 200
    data = analytics.json()
    assert data["published_shifts"] >= 1
    assert data["pending_shift_swaps"] == 0
    assert data["total_employees"] >= 1
    assert data["scheduled_hours"] >= 0

    cleanup_user(db, setup["employee_user_id"])
