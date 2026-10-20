"""Attachment storage abstraction with local-disk and S3 backends.

The active backend is chosen by config.DEPLOY_MODE. Both backends operate on an
opaque storage key (the stored filename), which is what the database records —
so switching modes requires no schema change.

  LocalStorage  (DEPLOY_MODE=local): reads/writes the local uploads/ directory
                and serves files via the app's own /api/uploads/{key} route.

  S3Storage     (DEPLOY_MODE=aws):   puts objects in an S3 bucket and serves
                them via short-lived presigned GET URLs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

import config

UPLOAD_DIR = Path(__file__).parent / "uploads"


class Storage(ABC):
    """Common interface for attachment storage backends."""

    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def url_for(self, key: str) -> str:
        """Return a URL the browser can use to fetch the object."""
        ...

    @abstractmethod
    def open_local(self, key: str):
        """Return a local filesystem path for the key, or None if not local.

        Used only by the local file-serving route; S3 returns None because it
        serves via presigned URLs instead.
        """
        ...


class LocalStorage(Storage):
    def __init__(self) -> None:
        UPLOAD_DIR.mkdir(exist_ok=True)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        (UPLOAD_DIR / key).write_bytes(data)

    def delete(self, key: str) -> None:
        p = UPLOAD_DIR / key
        if p.exists():
            p.unlink()

    def url_for(self, key: str) -> str:
        # Served by the app's own file route.
        return f"/api/uploads/{key}"

    def open_local(self, key: str):
        p = UPLOAD_DIR / key
        return p if p.exists() and p.is_file() else None


class S3Storage(Storage):
    def __init__(self) -> None:
        import boto3  # lazy: only in AWS mode

        self._s3 = boto3.client("s3", region_name=config.AWS_REGION)
        self._bucket = config.UPLOADS_BUCKET
        if not self._bucket:
            raise RuntimeError("DEPLOY_MODE=aws requires UPLOADS_BUCKET to be set")

    def save(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            # SSE handled by bucket default (SSE-KMS multi-region key).
        )

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)

    def url_for(self, key: str) -> str:
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=config.PRESIGN_TTL_SECONDS,
        )

    def open_local(self, key: str):
        return None  # S3 objects are served via presigned URLs, not local files


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """Return the process-wide storage backend for the active deploy mode."""
    return S3Storage() if config.IS_AWS else LocalStorage()
