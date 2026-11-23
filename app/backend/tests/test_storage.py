"""Tests for the storage abstraction (storage.py).

Local backend is exercised against a temp dir. The S3 backend is exercised with
a stubbed boto3 client so no AWS calls are made.
"""

import sys


def test_local_storage_roundtrip(config_in_mode, tmp_path, monkeypatch):
    config_in_mode("local")
    import storage

    # Point the local backend at a temp dir.
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()

    s = storage.get_storage()
    assert isinstance(s, storage.LocalStorage)

    s.save("abc.txt", b"hello", "text/plain")
    assert (tmp_path / "abc.txt").read_bytes() == b"hello"
    assert s.object_size("abc.txt") == 5
    assert s.url_for("abc.txt") == "/api/uploads/abc.txt"
    assert s.open_local("abc.txt") == tmp_path / "abc.txt"

    s.delete("abc.txt")
    assert not (tmp_path / "abc.txt").exists()
    assert s.open_local("abc.txt") is None
    assert s.object_size("abc.txt") is None


def test_s3_storage_uses_presigned_urls(config_in_mode, monkeypatch):
    config_in_mode("aws", UPLOADS_BUCKET="test-bucket", AWS_REGION="us-east-1")
    import storage

    calls = {}

    class FakeS3:
        def put_object(self, **kw):
            calls["put"] = kw

        def delete_object(self, **kw):
            calls["delete"] = kw

        def generate_presigned_url(self, op, Params, ExpiresIn):  # noqa: N803 (boto3 API names)
            calls["presign"] = (op, Params, ExpiresIn)
            return "https://signed.example/obj"

        def create_multipart_upload(self, **kw):
            calls["create_multipart"] = kw
            return {"UploadId": "test-upload-id"}

        def complete_multipart_upload(self, **kw):
            calls["complete_multipart"] = kw

        def abort_multipart_upload(self, **kw):
            calls["abort_multipart"] = kw

    # Stub boto3 so S3Storage() builds without AWS.
    import types

    fake_boto3 = types.SimpleNamespace(client=lambda *a, **k: FakeS3())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    storage.get_storage.cache_clear()

    s = storage.get_storage()
    assert isinstance(s, storage.S3Storage)

    s.save("k.jpg", b"img", "image/jpeg")
    assert calls["put"]["Bucket"] == "test-bucket"
    assert calls["put"]["Key"] == "k.jpg"

    url = s.url_for("k.jpg")
    assert url == "https://signed.example/obj"
    assert calls["presign"][1] == {"Bucket": "test-bucket", "Key": "k.jpg"}

    put_url = s.presigned_put_url("clip.mov", "video/quicktime")
    assert put_url == "https://signed.example/obj"
    # Do not bind ContentType into the signature: iOS Safari can normalize a
    # MIME type between initiate and PUT, which otherwise returns an opaque
    # cross-origin SignatureDoesNotMatch error.
    assert calls["presign"][1] == {"Bucket": "test-bucket", "Key": "clip.mov"}
    assert calls["presign"][2] == 3600

    upload_id = s.create_multipart_upload("clip.mov", "video/quicktime")
    assert upload_id == "test-upload-id"
    assert calls["create_multipart"] == {
        "Bucket": "test-bucket", "Key": "clip.mov", "ContentType": "video/quicktime"
    }
    part_url = s.presigned_part_url("clip.mov", upload_id, 2)
    assert part_url == "https://signed.example/obj"
    assert calls["presign"] == (
        "upload_part",
        {"Bucket": "test-bucket", "Key": "clip.mov", "UploadId": "test-upload-id", "PartNumber": 2},
        3600,
    )
    s.complete_multipart_upload("clip.mov", upload_id, [{"PartNumber": 1, "ETag": '"etag"'}])
    assert calls["complete_multipart"]["MultipartUpload"] == {
        "Parts": [{"PartNumber": 1, "ETag": '"etag"'}]
    }
    s.abort_multipart_upload("clip.mov", upload_id)
    assert calls["abort_multipart"] == {
        "Bucket": "test-bucket", "Key": "clip.mov", "UploadId": "test-upload-id"
    }

    # S3 never serves from local disk.
    assert s.open_local("k.jpg") is None

    s.delete("k.jpg")
    assert calls["delete"] == {"Bucket": "test-bucket", "Key": "k.jpg"}
