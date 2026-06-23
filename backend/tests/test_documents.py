"""Employee document upload API tests (Week 4 Day 24–25)."""

import boto3
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import cleanup_user
from tests.test_scheduling import _setup_org_scheduling

pytestmark = pytest.mark.usefixtures("mock_s3")


@pytest.fixture
def employee_setup(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    yield setup
    cleanup_user(db, setup["employee_user_id"])


def _upload_document(
    client: TestClient,
    org_id: str,
    headers: dict[str, str],
    employee_id: str,
    *,
    file_name: str = "certificate.pdf",
    content: bytes = b"%PDF-1.4 test document",
    content_type: str = "application/pdf",
) -> dict:
    size_bytes = len(content)
    presign = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=headers,
        json={
            "employee_id": employee_id,
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": file_name,
            "content_type": content_type,
            "size_bytes": size_bytes,
        },
    )
    assert presign.status_code == 200, presign.text
    presign_data = presign.json()

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.put_object(
        Bucket="shiftops-test-bucket",
        Key=presign_data["s3_key"],
        Body=content,
        ContentType=content_type,
    )

    complete = client.post(
        f"/organizations/{org_id}/documents/complete-upload",
        headers=headers,
        json={
            "document_id": presign_data["document_id"],
            "employee_id": employee_id,
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": file_name,
            "s3_key": presign_data["s3_key"],
            "content_type": content_type,
            "size_bytes": size_bytes,
        },
    )
    assert complete.status_code == 201, complete.text
    return complete.json()


def test_presign_upload_returns_url(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    response = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "training.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1200,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["upload_url"]
    assert data["s3_key"].startswith(
        f"orgs/{org_id}/employees/{setup['employee_user_id']}/documents/"
    )


def test_employee_can_upload_and_list_own_documents(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    document = _upload_document(
        client,
        org_id,
        setup["employee_headers"],
        setup["employee_user_id"],
    )
    assert document["file_name"] == "certificate.pdf"

    listed = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=setup["employee_headers"],
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_manager_can_list_employee_documents(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    _upload_document(client, org_id, setup["employee_headers"], setup["employee_user_id"])

    response = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_invalid_file_type_rejected(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    response = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "virus.exe",
            "content_type": "application/octet-stream",
            "size_bytes": 100,
        },
    )
    assert response.status_code == 400


def test_complete_upload_without_s3_object_fails(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    presign = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "missing.pdf",
            "content_type": "application/pdf",
            "size_bytes": 100,
        },
    ).json()

    response = client.post(
        f"/organizations/{org_id}/documents/complete-upload",
        headers=setup["employee_headers"],
        json={
            "document_id": presign["document_id"],
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "missing.pdf",
            "s3_key": presign["s3_key"],
            "content_type": "application/pdf",
            "size_bytes": 100,
        },
    )
    assert response.status_code == 400
