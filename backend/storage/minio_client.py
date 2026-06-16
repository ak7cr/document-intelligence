import io
import os
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

DOCUMENT_BUCKET = os.getenv("MINIO_BUCKET", "tender-documents")

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
    return _client


def ensure_bucket(bucket: str) -> None:
    client = get_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(
    bucket: str,
    object_key: str,
    data: bytes,
    content_type: str = "application/octet-stream",
) -> None:
    client = get_client()
    ensure_bucket(bucket)
    client.put_object(
        bucket,
        object_key,
        io.BytesIO(data),
        len(data),
        content_type=content_type,
    )


def get_presigned_url(
    bucket: str, object_key: str, expires_hours: int = 1
) -> str:
    client = get_client()
    return client.presigned_get_object(
        bucket,
        object_key,
        expires=timedelta(hours=expires_hours),
    )


def delete_file(bucket: str, object_key: str) -> None:
    client = get_client()
    try:
        client.remove_object(bucket, object_key)
    except S3Error:
        pass


CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "csv": "text/csv",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "tif": "image/tiff",
}
