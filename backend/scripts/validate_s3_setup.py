#!/usr/bin/env python3
"""Validate local AWS S3 configuration before implementing document uploads."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

TEST_KEY = "test/validate-s3-setup.txt"
TEST_BODY = b"shiftops s3 setup validation"


def _check_env_vars() -> bool:
    print("Checking environment variables...")
    checks = {
        "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
        "AWS_REGION": settings.aws_region,
        "S3_BUCKET_NAME": settings.s3_bucket_name,
    }
    ok = True
    for name, value in checks.items():
        if not value.strip():
            print(f"  FAIL  {name} is missing or empty")
            ok = False
        elif "SECRET" in name or name == "AWS_ACCESS_KEY_ID":
            print(f"  OK    {name} is set")
        else:
            print(f"  OK    {name} = {value}")
    return ok


def _likely_cause(error: Exception) -> str:
    message = str(error).lower()
    if "invalidaccesskeyid" in message or "signaturedoesnotmatch" in message:
        return "Invalid AWS access key or secret"
    if "nosuchbucket" in message:
        return "Bucket name is wrong or bucket is in a different region/account"
    if "accessdenied" in message or "403" in message:
        return "IAM user lacks required S3 permission (put/head/delete object)"
    if "could not connect" in message or "endpoint" in message:
        return "Network issue or wrong AWS region"
    return "See error details below"


def main() -> int:
    print("ShiftOps S3 setup validation\n")

    if not _check_env_vars():
        print("\nResult: FAILED — fix missing env vars in backend/.env")
        return 1

    print("\nCreating boto3 S3 client...")
    try:
        import boto3

        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )
        print("  OK    boto3 client created")
    except (BotoCoreError, ImportError) as exc:
        print(f"  FAIL  Could not create boto3 client: {exc}")
        return 1

    bucket = settings.s3_bucket_name
    print(f"\nTesting object permissions on s3://{bucket}/{TEST_KEY}")

    try:
        client.put_object(Bucket=bucket, Key=TEST_KEY, Body=TEST_BODY, ContentType="text/plain")
        print("  OK    put_object worked")
    except ClientError as exc:
        print(f"  FAIL  put_object: {exc}")
        print(f"        Likely cause: {_likely_cause(exc)}")
        return 1

    try:
        client.head_object(Bucket=bucket, Key=TEST_KEY)
        print("  OK    head_object worked")
    except ClientError as exc:
        print(f"  FAIL  head_object: {exc}")
        print(f"        Likely cause: {_likely_cause(exc)}")
        return 1

    try:
        client.delete_object(Bucket=bucket, Key=TEST_KEY)
        print("  OK    delete_object worked")
    except ClientError as exc:
        print(f"  FAIL  delete_object: {exc}")
        print(f"        Likely cause: {_likely_cause(exc)}")
        return 1

    print("\nResult: ALL PASSED — S3 setup is ready for Day 24 coding.")
    print("Next: implement presigned upload flow in the backend.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
