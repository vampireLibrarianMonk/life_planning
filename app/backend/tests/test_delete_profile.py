"""Archive -> delete (with handshake) -> restore round-trip integrity.

Exercises the full backup/restore story end-to-end at the route-function level
(no HTTP client needed): populate a profile across every table incl. an
attachment + avatar blob in storage, archive it to a zip, require the archive
token to delete, confirm the DB + blobs are gone, then restore from the zip and
confirm everything (rows + blobs + original IDs) comes back.
"""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "storage", "main"):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    archive = importlib.import_module("routes.archive")

    # Point local storage at a temp dir so blob save/read/delete is isolated.
    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    return archive, models, storage, TestSession()


class _Admin:
    role = None


def _seed(models, storage, db):
    st = storage.get_storage()
    st.save("avatar_x.png", b"AVATARBYTES", "image/png")
    profile = models.Profile(name="RoundTrip", date_of_birth="2015-01-01", avatar="avatar_x.png")
    db.add(profile)
    db.flush()
    pid = profile.id

    entry = models.PillarEntry(
        profile_id=pid, pillar=models.Pillar.heritage, title="entry", is_milestone=1
    )
    db.add(entry)
    db.flush()
    st.save("att_1.jpg", b"ATTACHMENTBYTES", "image/jpeg")
    db.add(
        models.EventAttachment(
            entry_id=entry.id, filename="att_1.jpg", original_name="a.jpg", mime_type="image/jpeg"
        )
    )
    bounty = models.Bounty(profile_id=pid, tier=models.BountyTier.bronze, title="b")
    db.add(bounty)
    db.flush()
    db.add(models.BountyLog(bounty_id=bounty.id, author="parent", content="log"))
    db.add(models.DiscernmentJournal(profile_id=pid, category="faith", title="t", reflection="r"))
    db.add(models.WishlistItem(profile_id=pid, title="bike", cost_cents=1000))
    db.commit()
    return pid


def test_archive_delete_restore_roundtrip(ctx):
    archive, models, storage, db = ctx
    admin = _Admin()
    admin.role = models.Role.admin

    pid = _seed(models, storage, db)

    # ARCHIVE -> stream zip + token.
    resp = archive.archive_profile(profile_id=pid, db=db, _=admin)
    token = resp.headers["X-Archive-Token"]
    # Consume the StreamingResponse body (sync or async iterator of bytes/str).
    import asyncio

    async def _drain(it):
        chunks = []
        async for c in it:
            chunks.append(c if isinstance(c, bytes) else c.encode())
        return b"".join(chunks)

    zip_bytes = asyncio.get_event_loop().run_until_complete(_drain(resp.body_iterator))
    assert zip_bytes[:2] == b"PK"  # a real zip

    # DELETE without a token must fail.
    with pytest.raises(HTTPException) as bad:
        archive.delete_profile(profile_id=pid, archive_token="garbage", db=db, _=admin)
    assert bad.value.status_code == 403

    # DELETE with the token removes rows AND blobs.
    archive.delete_profile(profile_id=pid, archive_token=token, db=db, _=admin)
    assert db.query(models.Profile).filter(models.Profile.id == pid).first() is None
    assert db.query(models.BountyLog).count() == 0
    assert storage.get_storage().read("avatar_x.png") is None
    assert storage.get_storage().read("att_1.jpg") is None

    # RESTORE from the archive recreates everything with the ORIGINAL id.
    class _UF:
        async def read(self):
            return zip_bytes

    result = asyncio.get_event_loop().run_until_complete(
        archive.restore_profile(file=_UF(), db=db, _=admin)
    )
    assert result["profile_id"] == pid
    assert db.query(models.Profile).filter(models.Profile.id == pid).first() is not None
    assert db.query(models.DiscernmentJournal).filter_by(profile_id=pid).count() == 1
    assert db.query(models.WishlistItem).filter_by(profile_id=pid).count() == 1
    assert db.query(models.BountyLog).count() == 1  # grandchild restored
    # Blobs restored.
    assert storage.get_storage().read("avatar_x.png") == b"AVATARBYTES"
    assert storage.get_storage().read("att_1.jpg") == b"ATTACHMENTBYTES"

    # Restoring again (id now exists) must hard-fail.
    class _UF2:
        async def read(self):
            return zip_bytes

    with pytest.raises(HTTPException) as conflict:
        asyncio.get_event_loop().run_until_complete(
            archive.restore_profile(file=_UF2(), db=db, _=admin)
        )
    assert conflict.value.status_code == 409


def test_delete_requires_matching_profile_token(ctx):
    archive, models, storage, db = ctx
    admin = _Admin()
    admin.role = models.Role.admin
    pid = _seed(models, storage, db)
    # A token minted for a DIFFERENT profile must not authorize this delete.
    other_token = archive._mint_archive_token(pid + 999)
    with pytest.raises(HTTPException) as exc:
        archive.delete_profile(profile_id=pid, archive_token=other_token, db=db, _=admin)
    assert exc.value.status_code == 403
