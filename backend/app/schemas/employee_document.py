import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentType


class PresignUploadRequest(BaseModel):
    employee_id: uuid.UUID
    document_type: DocumentType
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)


class PresignUploadResponse(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    s3_key: str
    expires_in: int


class CompleteUploadRequest(BaseModel):
    document_id: uuid.UUID
    employee_id: uuid.UUID
    document_type: DocumentType
    file_name: str = Field(min_length=1, max_length=255)
    s3_key: str = Field(min_length=1, max_length=512)
    content_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(gt=0)


class EmployeeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    employee_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID
    document_type: DocumentType
    file_name: str
    content_type: str
    size_bytes: int
    created_at: datetime
    employee_name: str | None = None
    uploaded_by_name: str | None = None


class PresignDownloadResponse(BaseModel):
    download_url: str
    expires_in: int
    file_name: str
    content_type: str


def employee_document_to_response(document) -> EmployeeDocumentResponse:
    return EmployeeDocumentResponse(
        id=document.id,
        organization_id=document.organization_id,
        employee_id=document.employee_id,
        uploaded_by_user_id=document.uploaded_by_user_id,
        document_type=document.document_type,
        file_name=document.file_name,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        created_at=document.created_at,
        employee_name=document.employee.full_name if document.employee else None,
        uploaded_by_name=document.uploaded_by.full_name if document.uploaded_by else None,
    )
