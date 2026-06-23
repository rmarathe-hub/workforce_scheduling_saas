import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.employee_document import (
    CompleteUploadRequest,
    EmployeeDocumentResponse,
    PresignDownloadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    employee_document_to_response,
)
from app.services.document_service import (
    complete_document_upload,
    create_presigned_download,
    create_presigned_upload,
    delete_employee_document,
    list_employee_documents,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["documents"])


@router.post("/documents/presign-upload", response_model=PresignUploadResponse)
def presign_upload(
    organization_id: uuid.UUID,
    payload: PresignUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresignUploadResponse:
    return create_presigned_upload(db, organization_id, current_user, payload)


@router.post(
    "/documents/complete-upload",
    response_model=EmployeeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def complete_upload(
    organization_id: uuid.UUID,
    payload: CompleteUploadRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmployeeDocumentResponse:
    document = complete_document_upload(db, organization_id, current_user, payload)
    return employee_document_to_response(document)


@router.get(
    "/employees/{employee_id}/documents",
    response_model=list[EmployeeDocumentResponse],
)
def list_documents_for_employee(
    organization_id: uuid.UUID,
    employee_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EmployeeDocumentResponse]:
    documents = list_employee_documents(db, organization_id, current_user, employee_id)
    return [employee_document_to_response(document) for document in documents]


@router.get(
    "/documents/{document_id}/download-url",
    response_model=PresignDownloadResponse,
)
def presign_download(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresignDownloadResponse:
    return create_presigned_download(db, organization_id, current_user, document_id)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    delete_employee_document(db, organization_id, current_user, document_id)
