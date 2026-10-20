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
    assert s.url_for("abc.txt") == "/api/uploads/abc.txt"
    assert s.open_local("abc.txt") == tmp_path / "abc.txt"

    s.delete("abc.txt")
    assert not (tmp_path / "abc.txt").exists()
    assert s.open_local("abc.txt") is None


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

    # S3 never serves from local disk.
    assert s.open_local("k.jpg") is None

    s.delete("k.jpg")
    assert calls["delete"] == {"Bucket": "test-bucket", "Key": "k.jpg"}
