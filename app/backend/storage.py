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
    def read(self, key: str) -> bytes | None:
        """Return the stored bytes for a key, or None if it doesn't exist."""
        ...

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

    @abstractmethod
    def presigned_put_url(self, key: str, content_type: str) -> str:
        """Return a URL the browser can PUT bytes to DIRECTLY (bypassing the app).

        S3: a short-lived presigned PUT URL to the bucket (so large videos never
        pass through the App Runner request body / its size cap).
        Local: an app-served endpoint (/api/uploads/direct/{key}) that accepts a
        raw PUT, so the same two-step upload flow works identically in dev/tests.
        """
        ...

    @abstractmethod
    def create_multipart_upload(self, key: str, content_type: str) -> str: ...

    @abstractmethod
    def presigned_part_url(self, key: str, upload_id: str, part_number: int) -> str: ...

    @abstractmethod
    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None: ...

    @abstractmethod
    def abort_multipart_upload(self, key: str, upload_id: str) -> None: ...

    def exists(self, key: str) -> bool:
        """Whether an object is present (used to finalize direct uploads)."""
        return self.read(key) is not None

    @abstractmethod
    def object_size(self, key: str) -> int | None:
        """Return the stored byte size, or None when the object is absent."""
        ...


class LocalStorage(Storage):
    def __init__(self) -> None:
        UPLOAD_DIR.mkdir(exist_ok=True)

    def save(self, key: str, data: bytes, content_type: str) -> None:
        (UPLOAD_DIR / key).write_bytes(data)

    def read(self, key: str) -> bytes | None:
        p = UPLOAD_DIR / key
        return p.read_bytes() if p.exists() and p.is_file() else None

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

    def presigned_put_url(self, key: str, content_type: str) -> str:
        # No real presigning for local disk: hand back the app's own direct-PUT
        # endpoint so the browser/tests use the identical two-step flow.
        return f"/api/uploads/direct/{key}"

    def create_multipart_upload(self, key: str, content_type: str) -> str:
        return key

    def presigned_part_url(self, key: str, upload_id: str, part_number: int) -> str:
        return f"/api/uploads/direct/{key}"

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None:
        return None

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        return None

    def object_size(self, key: str) -> int | None:
        path = self.open_local(key)
        return path.stat().st_size if path else None


class S3Storage(Storage):
    def __init__(self) -> None:
        import boto3  # lazy: only in AWS mode
        from botocore.config import Config

        # SigV4 is REQUIRED for presigned URLs against a KMS-encrypted bucket
        # (S3 rejects SigV2 with InvalidArgument otherwise). Pin it explicitly.
        self._s3 = boto3.client(
            "s3",
            region_name=config.AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
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

    def read(self, key: str) -> bytes | None:
        try:
            resp = self._s3.get_object(Bucket=self._bucket, Key=key)
            return resp["Body"].read()
        except self._s3.exceptions.NoSuchKey:
            return None

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

    def presigned_put_url(self, key: str, content_type: str) -> str:
        """Return a direct-upload URL without signing the Content-Type header.

        The client still supplies Content-Type, and S3 stores that value as
        object metadata. Binding it into the SigV4 signature made harmless
        browser-side MIME normalization (notably on iOS Safari) turn into an
        opaque cross-origin ``SignatureDoesNotMatch`` failure. The gallery
        already validates the declared MIME family before issuing this URL, so
        signing that client-controlled header provides no meaningful extra
        protection.
        """
        return self._s3.generate_presigned_url(
            "put_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=config.PRESIGN_TTL_SECONDS,
        )

    def create_multipart_upload(self, key: str, content_type: str) -> str:
        return self._s3.create_multipart_upload(
            Bucket=self._bucket, Key=key, ContentType=content_type
        )["UploadId"]

    def presigned_part_url(self, key: str, upload_id: str, part_number: int) -> str:
        return self._s3.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "UploadId": upload_id,
                "PartNumber": part_number,
            },
            ExpiresIn=config.PRESIGN_TTL_SECONDS,
        )

    def complete_multipart_upload(self, key: str, upload_id: str, parts: list[dict]) -> None:
        self._s3.complete_multipart_upload(
            Bucket=self._bucket, Key=key, UploadId=upload_id, MultipartUpload={"Parts": parts}
        )

    def abort_multipart_upload(self, key: str, upload_id: str) -> None:
        self._s3.abort_multipart_upload(Bucket=self._bucket, Key=key, UploadId=upload_id)

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001 - any 404/403/client error -> treat as absent
            return False

    def object_size(self, key: str) -> int | None:
        try:
            return self._s3.head_object(Bucket=self._bucket, Key=key)["ContentLength"]
        except Exception:  # noqa: BLE001 - any 404/403/client error -> treat as absent
            return None


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    """Return the process-wide storage backend for the active deploy mode."""
    return S3Storage() if config.IS_AWS else LocalStorage()
