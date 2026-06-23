"""AWS S3 helpers for employee document uploads."""

from __future__ import annotations

import re
import uuid
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from app.config import settings

PRESIGNED_URL_EXPIRES_SECONDS = 3600


@lru_cache
def get_s3_client():
    return boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )


def ensure_s3_configured() -> None:
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        raise RuntimeError("AWS credentials are not configured")
    if not settings.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is not configured")


def sanitize_filename(filename: str) -> str:
    base = filename.split("/")[-1].split("\\")[-1].strip()
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    return safe[:200] or "document"


def build_document_s3_key(
    organization_id: uuid.UUID,
    employee_id: uuid.UUID,
    document_id: uuid.UUID,
    filename: str,
) -> str:
    safe_name = sanitize_filename(filename)
    return (
        f"orgs/{organization_id}/employees/{employee_id}/documents/"
        f"{document_id}-{safe_name}"
    )


def generate_presigned_upload_url(s3_key: str, content_type: str) -> str:
    ensure_s3_configured()
    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRES_SECONDS,
    )


def generate_presigned_download_url(
    s3_key: str,
    *,
    file_name: str,
    content_type: str,
) -> str:
    ensure_s3_configured()
    client = get_s3_client()
    safe_name = sanitize_filename(file_name)
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": s3_key,
            "ResponseContentDisposition": f'inline; filename="{safe_name}"',
            "ResponseContentType": content_type,
        },
        ExpiresIn=PRESIGNED_URL_EXPIRES_SECONDS,
    )


def object_exists(s3_key: str) -> bool:
    ensure_s3_configured()
    client = get_s3_client()
    try:
        client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return True
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def get_object_size(s3_key: str) -> int:
    ensure_s3_configured()
    client = get_s3_client()
    response = client.head_object(Bucket=settings.s3_bucket_name, Key=s3_key)
    return int(response["ContentLength"])


def delete_object(s3_key: str) -> None:
    ensure_s3_configured()
    client = get_s3_client()
    client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
