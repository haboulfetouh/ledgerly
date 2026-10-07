import io
from functools import lru_cache

from minio import Minio

from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
        region="us-east-1",
    )


@lru_cache
def get_minio_public_client() -> Minio:
    """Same credentials, but signed against the browser-reachable host —
    used only for presigned URLs, never for server-side put/get.

    `region` is pinned explicitly: without it, minio-py calls
    GetBucketLocation against the configured endpoint before signing —
    which fails here since "localhost:9000" (correct for the browser)
    doesn't resolve to MinIO from inside this container.
    """
    settings = get_settings()
    return Minio(
        settings.minio_public_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
        region="us-east-1",
    )


def object_key(tenant_id: str, invoice_id: str, filename: str) -> str:
    return f"{tenant_id}/{invoice_id}/{filename}"


def upload_document(key: str, data: bytes, content_type: str) -> None:
    settings = get_settings()
    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        key,
        io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )


def download_document(key: str) -> bytes:
    settings = get_settings()
    client = get_minio_client()
    response = client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presigned_url(key: str, expires_seconds: int = 3600) -> str:
    from datetime import timedelta

    settings = get_settings()
    client = get_minio_public_client()
    return client.presigned_get_object(
        settings.minio_bucket, key, expires=timedelta(seconds=expires_seconds)
    )
