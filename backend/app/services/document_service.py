"""Employee document upload business logic."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.auth.permissions import require_min_role
from app.models.employee_document import EmployeeDocument
from app.models.employee_profile import EmployeeProfile
from app.models.enums import DocumentType, MembershipRole, NotificationType
from app.models.user import User
from app.schemas.employee_document import (
    CompleteUploadRequest,
    PresignDownloadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.services.s3_service import (
    PRESIGNED_URL_EXPIRES_SECONDS,
    build_document_s3_key,
    delete_object,
    generate_presigned_download_url,
    generate_presigned_upload_url,
    get_object_size,
    object_exists,
)
from app.services.notification_service import notify_managers

ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
)
MAX_DOCUMENT_SIZE_BYTES = 5 * 1024 * 1024


def _get_org_employee_profile(
    db: Session, organization_id: uuid.UUID, employee_id: uuid.UUID
) -> EmployeeProfile:
    profile = db.scalar(
        select(EmployeeProfile).where(
            EmployeeProfile.organization_id == organization_id,
            EmployeeProfile.user_id == employee_id,
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found in this organization",
        )
    return profile


def _ensure_document_access(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    employee_id: uuid.UUID,
) -> None:
    _get_org_employee_profile(db, organization_id, employee_id)

    if current_user.id == employee_id:
        require_min_role(db, organization_id, current_user, MembershipRole.EMPLOYEE)
        return

    require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)


def _validate_upload_payload(
    content_type: str,
    size_bytes: int,
    file_name: str,
) -> None:
    if not file_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File name is required",
        )
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File type not allowed. Use PDF, JPEG, or PNG.",
        )
    if size_bytes <= 0 or size_bytes > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size must be between 1 byte and {MAX_DOCUMENT_SIZE_BYTES} bytes",
        )


def create_presigned_upload(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    payload: PresignUploadRequest,
) -> PresignUploadResponse:
    if current_user.id != payload.employee_id:
        require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    else:
        _ensure_document_access(db, organization_id, current_user, payload.employee_id)
    _validate_upload_payload(payload.content_type, payload.size_bytes, payload.file_name)

    document_id = uuid.uuid4()
    s3_key = build_document_s3_key(
        organization_id,
        payload.employee_id,
        document_id,
        payload.file_name,
    )
    upload_url = generate_presigned_upload_url(s3_key, payload.content_type)

    return PresignUploadResponse(
        document_id=document_id,
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in=PRESIGNED_URL_EXPIRES_SECONDS,
    )


def complete_document_upload(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    payload: CompleteUploadRequest,
) -> EmployeeDocument:
    if current_user.id != payload.employee_id:
        require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)
    else:
        _ensure_document_access(db, organization_id, current_user, payload.employee_id)
    _validate_upload_payload(payload.content_type, payload.size_bytes, payload.file_name)

    expected_prefix = f"orgs/{organization_id}/employees/{payload.employee_id}/documents/"
    if not payload.s3_key.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid S3 key for this organization and employee",
        )
    if str(payload.document_id) not in payload.s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 key does not match document id",
        )

    if not object_exists(payload.s3_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file not found in S3. Complete upload after PUT succeeds.",
        )

    actual_size = get_object_size(payload.s3_key)
    if actual_size > MAX_DOCUMENT_SIZE_BYTES:
        delete_object(payload.s3_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file exceeds maximum allowed size",
        )

    existing = db.scalar(
        select(EmployeeDocument).where(EmployeeDocument.s3_key == payload.s3_key)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document already registered",
        )

    document = EmployeeDocument(
        id=payload.document_id,
        organization_id=organization_id,
        employee_id=payload.employee_id,
        uploaded_by_user_id=current_user.id,
        document_type=payload.document_type,
        file_name=payload.file_name,
        s3_key=payload.s3_key,
        content_type=payload.content_type,
        size_bytes=actual_size,
    )
    db.add(document)
    notify_managers(
        db,
        organization_id=organization_id,
        notification_type=NotificationType.DOCUMENT_UPLOADED,
        title="Employee document uploaded",
        message=f"A new document ({payload.file_name}) was uploaded.",
        entity_type="employee_document",
        entity_id=document.id,
    )
    db.commit()
    return _load_document(db, document.id)


def list_employee_documents(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    employee_id: uuid.UUID,
) -> list[EmployeeDocument]:
    _ensure_document_access(db, organization_id, current_user, employee_id)

    return list(
        db.scalars(
            select(EmployeeDocument)
            .where(
                EmployeeDocument.organization_id == organization_id,
                EmployeeDocument.employee_id == employee_id,
            )
            .options(
                selectinload(EmployeeDocument.employee),
                selectinload(EmployeeDocument.uploaded_by),
            )
            .order_by(EmployeeDocument.created_at.desc())
        ).all()
    )


def get_document(
    db: Session,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
) -> EmployeeDocument:
    document = db.scalar(
        select(EmployeeDocument)
        .where(
            EmployeeDocument.id == document_id,
            EmployeeDocument.organization_id == organization_id,
        )
        .options(
            selectinload(EmployeeDocument.employee),
            selectinload(EmployeeDocument.uploaded_by),
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def create_presigned_download(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    document_id: uuid.UUID,
) -> PresignDownloadResponse:
    document = get_document(db, organization_id, document_id)
    _ensure_document_access(db, organization_id, current_user, document.employee_id)

    download_url = generate_presigned_download_url(
        document.s3_key,
        file_name=document.file_name,
        content_type=document.content_type,
    )
    return PresignDownloadResponse(
        download_url=download_url,
        expires_in=PRESIGNED_URL_EXPIRES_SECONDS,
        file_name=document.file_name,
        content_type=document.content_type,
    )


def delete_employee_document(
    db: Session,
    organization_id: uuid.UUID,
    current_user: User,
    document_id: uuid.UUID,
) -> None:
    document = get_document(db, organization_id, document_id)
    _ensure_document_access(db, organization_id, current_user, document.employee_id)

    if current_user.id != document.employee_id:
        require_min_role(db, organization_id, current_user, MembershipRole.MANAGER)

    delete_object(document.s3_key)
    db.delete(document)
    db.commit()


def _load_document(db: Session, document_id: uuid.UUID) -> EmployeeDocument:
    document = db.scalar(
        select(EmployeeDocument)
        .where(EmployeeDocument.id == document_id)
        .options(
            selectinload(EmployeeDocument.employee),
            selectinload(EmployeeDocument.uploaded_by),
        )
    )
    assert document is not None
    return document
