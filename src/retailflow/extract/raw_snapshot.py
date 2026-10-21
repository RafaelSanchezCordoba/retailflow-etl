"""Upload an orders CSV snapshot to the S3 raw zone, keyed by logical date."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import boto3


@dataclass
class UploadResult:
    path: Path
    key: str
    bucket: str


def client_from_env():
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION", "eu-north-1"))


def bucket_from_env() -> str:
    return os.environ["RAW_BUCKET_NAME"]


def upload_file(path: Path, ds: str, client, bucket: str) -> UploadResult:
    """Upload one orders CSV to raw/orders/ingestion_date=<ds>/<filename>.

    Re-running the same (path, ds) overwrites the same key; bucket versioning
    (infrastructure/terraform/s3.tf) keeps prior content recoverable, so this
    stays safe to repeat on a backfill or rerun.
    """
    key = f"raw/orders/ingestion_date={ds}/{path.name}"
    client.upload_file(str(path), bucket, key)
    return UploadResult(path=path, key=key, bucket=bucket)


def main() -> None:
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/samples/orders")
    client = client_from_env()
    bucket = bucket_from_env()
    for path in sorted(directory.glob("orders_*.csv")):
        ds = path.stem.removeprefix("orders_")
        result = upload_file(path, ds, client, bucket)
        print(f"{result.path.name}: uploaded to s3://{result.bucket}/{result.key}")


if __name__ == "__main__":
    main()
