"""Document access control and security tests (Week 4 Day 25)."""

import uuid

import boto3
import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.document_service import MAX_DOCUMENT_SIZE_BYTES
from tests.helpers import add_employee_member, cleanup_user, register_user_with_org
from tests.test_documents import _upload_document
from tests.test_scheduling import _setup_org_scheduling

pytestmark = pytest.mark.usefixtures("mock_s3")


@pytest.fixture
def employee_setup(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    yield setup
    cleanup_user(db, setup["employee_user_id"])


@pytest.fixture
def two_employee_setup(
    client: TestClient, db: Session, org_id: str, auth_headers: dict[str, str]
) -> dict[str, str]:
    setup = _setup_org_scheduling(client, org_id, auth_headers)
    second = add_employee_member(client, org_id, auth_headers)
    yield {**setup, "employee2_user_id": second["user_id"], "employee2_headers": second["headers"]}
    cleanup_user(db, second["user_id"])
    cleanup_user(db, setup["employee_user_id"])


def test_response_does_not_expose_s3_key(
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
    assert "s3_key" not in document

    listed = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=setup["employee_headers"],
    )
    assert listed.status_code == 200
    assert "s3_key" not in listed.json()[0]


def test_employee_cannot_upload_for_another_employee(
    client: TestClient,
    org_id: str,
    two_employee_setup: dict[str, str],
) -> None:
    setup = two_employee_setup
    response = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee2_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "training.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1200,
        },
    )
    assert response.status_code == 403


def test_employee_cannot_list_other_employee_documents(
    client: TestClient,
    org_id: str,
    two_employee_setup: dict[str, str],
) -> None:
    setup = two_employee_setup
    _upload_document(
        client,
        org_id,
        setup["employee2_headers"],
        setup["employee2_user_id"],
    )

    response = client.get(
        f"/organizations/{org_id}/employees/{setup['employee2_user_id']}/documents",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403


def test_cross_org_cannot_list_employee_documents(
    client: TestClient,
    db: Session,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    other_org = register_user_with_org(client)

    response = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=other_org["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, other_org["user_id"])


def test_cross_org_cannot_presign_upload(
    client: TestClient,
    db: Session,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    other_org = register_user_with_org(client)

    response = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=other_org["headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "training.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1200,
        },
    )
    assert response.status_code == 403

    cleanup_user(db, other_org["user_id"])


def test_cross_org_cannot_delete_document(
    client: TestClient,
    db: Session,
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
    other_org = register_user_with_org(client)

    response = client.delete(
        f"/organizations/{org_id}/documents/{document['id']}",
        headers=other_org["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, other_org["user_id"])


def test_oversized_file_rejected_at_presign(
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
            "file_name": "huge.pdf",
            "content_type": "application/pdf",
            "size_bytes": MAX_DOCUMENT_SIZE_BYTES + 1,
        },
    )
    assert response.status_code == 400


def test_oversized_s3_object_rejected_on_complete(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    oversized_body = b"x" * (MAX_DOCUMENT_SIZE_BYTES + 1)
    presign = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "huge.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    ).json()

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.put_object(
        Bucket="shiftops-test-bucket",
        Key=presign["s3_key"],
        Body=oversized_body,
        ContentType="application/pdf",
    )

    response = client.post(
        f"/organizations/{org_id}/documents/complete-upload",
        headers=setup["employee_headers"],
        json={
            "document_id": presign["document_id"],
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "huge.pdf",
            "s3_key": presign["s3_key"],
            "content_type": "application/pdf",
            "size_bytes": 1024,
        },
    )
    assert response.status_code == 400

    with pytest.raises(ClientError):
        s3_client.head_object(Bucket="shiftops-test-bucket", Key=presign["s3_key"])


def test_invalid_s3_key_rejected_on_complete(
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
            "file_name": "training.pdf",
            "content_type": "application/pdf",
            "size_bytes": 1200,
        },
    ).json()

    bad_key = f"orgs/{uuid.uuid4()}/employees/{setup['employee_user_id']}/documents/{uuid.uuid4()}-training.pdf"
    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.put_object(
        Bucket="shiftops-test-bucket",
        Key=bad_key,
        Body=b"%PDF-1.4 test",
        ContentType="application/pdf",
    )

    response = client.post(
        f"/organizations/{org_id}/documents/complete-upload",
        headers=setup["employee_headers"],
        json={
            "document_id": presign["document_id"],
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "training.pdf",
            "s3_key": bad_key,
            "content_type": "application/pdf",
            "size_bytes": 1200,
        },
    )
    assert response.status_code == 400


def test_delete_document_removes_metadata_and_s3_object(
    client: TestClient,
    org_id: str,
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    content = b"%PDF-1.4 delete test"
    presign = client.post(
        f"/organizations/{org_id}/documents/presign-upload",
        headers=setup["employee_headers"],
        json={
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "delete-me.pdf",
            "content_type": "application/pdf",
            "size_bytes": len(content),
        },
    ).json()
    s3_key = presign["s3_key"]

    s3_client = boto3.client("s3", region_name="us-east-1")
    s3_client.put_object(
        Bucket="shiftops-test-bucket",
        Key=s3_key,
        Body=content,
        ContentType="application/pdf",
    )

    complete = client.post(
        f"/organizations/{org_id}/documents/complete-upload",
        headers=setup["employee_headers"],
        json={
            "document_id": presign["document_id"],
            "employee_id": setup["employee_user_id"],
            "document_type": "TRAINING_CERTIFICATE",
            "file_name": "delete-me.pdf",
            "s3_key": s3_key,
            "content_type": "application/pdf",
            "size_bytes": len(content),
        },
    )
    document_id = complete.json()["id"]

    delete_response = client.delete(
        f"/organizations/{org_id}/documents/{document_id}",
        headers=setup["employee_headers"],
    )
    assert delete_response.status_code == 204

    listed = client.get(
        f"/organizations/{org_id}/employees/{setup['employee_user_id']}/documents",
        headers=setup["employee_headers"],
    )
    assert listed.status_code == 200
    assert listed.json() == []

    with pytest.raises(ClientError):
        s3_client.head_object(Bucket="shiftops-test-bucket", Key=s3_key)


def test_presign_download_returns_url_for_owner(
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

    response = client.get(
        f"/organizations/{org_id}/documents/{document['id']}/download-url",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 200
    data = response.json()
    assert data["download_url"]
    assert data["file_name"] == "certificate.pdf"
    assert data["expires_in"] > 0


def test_manager_can_get_download_url(
    client: TestClient,
    org_id: str,
    auth_headers: dict[str, str],
    employee_setup: dict[str, str],
) -> None:
    setup = employee_setup
    document = _upload_document(
        client,
        org_id,
        setup["employee_headers"],
        setup["employee_user_id"],
    )

    response = client.get(
        f"/organizations/{org_id}/documents/{document['id']}/download-url",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["download_url"]


def test_employee_cannot_download_other_employee_document(
    client: TestClient,
    org_id: str,
    two_employee_setup: dict[str, str],
) -> None:
    setup = two_employee_setup
    document = _upload_document(
        client,
        org_id,
        setup["employee2_headers"],
        setup["employee2_user_id"],
    )

    response = client.get(
        f"/organizations/{org_id}/documents/{document['id']}/download-url",
        headers=setup["employee_headers"],
    )
    assert response.status_code == 403


def test_cross_org_cannot_get_download_url(
    client: TestClient,
    db: Session,
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
    other_org = register_user_with_org(client)

    response = client.get(
        f"/organizations/{org_id}/documents/{document['id']}/download-url",
        headers=other_org["headers"],
    )
    assert response.status_code == 403

    cleanup_user(db, other_org["user_id"])
