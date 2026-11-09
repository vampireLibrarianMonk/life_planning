"""Gallery (canonical media) — Pass 1 adversarial + behavior tests.

Route-function level (no HTTP client, matching the repo convention). Covers the
release-gate cases from the v6 handoff that apply to this pass:

  AUTH-01  cross-profile list/get/delete is denied (no leak of another child's media)
  AUTH-02  objective-link tampering across profiles is denied
  RBAC-01  readonly cannot upload / edit / delete / link
  (archive) deactivating an age group / deleting an objective does NOT delete media
  REG-01   legacy EventAttachment path is untouched
"""

import asyncio
import importlib
import sys

import pytest
from fastapi import HTTPException, UploadFile


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in (
        "config",
        "database",
        "models",
        "auth",
        "storage",
        "main",
        "routes.gallery",
        "routes.child_development",
    ):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    gallery = importlib.import_module("routes.gallery")

    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    db = TestSession()

    # Two children + the three role actors.
    a = models.Profile(name="Child A", date_of_birth="2015-01-01")
    b = models.Profile(name="Child B", date_of_birth="2016-02-02")
    db.add_all([a, b])
    db.flush()

    admin = models.User(
        username="admin", hashed_password="x", display_name="Admin", role=models.Role.admin, id=1
    )
    readonly = models.User(
        username="gran", hashed_password="x", display_name="Gran", role=models.Role.readonly, id=2
    )
    db.add_all([admin, readonly])
    db.commit()

    return gallery, models, storage, db, a.id, b.id, admin, readonly


def _upload(gallery, db, pid, user, name="p.jpg", mime="image/jpeg", data=b"JPEGDATA"):
    import io

    from starlette.datastructures import Headers

    uf = UploadFile(
        filename=name,
        file=io.BytesIO(data),
        headers=Headers({"content-type": mime}),
    )
    return asyncio.run(gallery.upload_media(pid, files=[uf], db=db, current_user=user))


def test_upload_then_list_scoped_to_profile(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    out = _upload(gallery, db, a, admin, name="first.jpg")
    assert len(out) == 1 and out[0].media_type == "photo" and out[0].profile_id == a
    # A's gallery has it; B's is empty.
    assert len(gallery.list_gallery(a, db=db)) == 1
    assert len(gallery.list_gallery(b, db=db)) == 0


def test_auth01_cross_profile_get_and_delete_denied(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    media = _upload(gallery, db, a, admin)[0]
    # Fetch A's media while scoped to B -> 404, no leak.
    with pytest.raises(HTTPException) as e:
        gallery.get_media(b, media.id, db=db)
    assert e.value.status_code == 404
    # Delete A's media while scoped to B -> 404.
    with pytest.raises(HTTPException) as e:
        gallery.delete_media(b, media.id, db=db, _=admin)
    assert e.value.status_code == 404
    # Still present under A.
    assert len(gallery.list_gallery(a, db=db)) == 1


def test_auth02_cross_profile_objective_link_denied(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import ObjectiveLinkCreate

    media = _upload(gallery, db, a, admin)[0]
    # An objective that belongs to B, not A.
    obj_b = models.PillarEntry(
        profile_id=b, pillar=models.Pillar.heritage, title="B obj", is_milestone=1
    )
    db.add(obj_b)
    db.commit()
    with pytest.raises(HTTPException) as e:
        gallery.link_objective(
            a, media.id, ObjectiveLinkCreate(objective_id=obj_b.id), db=db, _=admin
        )
    assert e.value.status_code == 404  # objective not on this profile


def test_rbac01_readonly_cannot_write(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    # Uploads require admin/child; readonly must be rejected by require_admin_or_child.
    # (We call the guard directly to prove the dependency denies readonly.)
    from auth import require_admin_or_child

    with pytest.raises(HTTPException) as e:
        require_admin_or_child(current_user=ro)
    assert e.value.status_code == 403


def test_archive_media_survives_objective_delete(ctx):
    """THE bug fix: deleting the objective must NOT delete the gallery media."""
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import ObjectiveLinkCreate

    media = _upload(gallery, db, a, admin)[0]
    obj = models.PillarEntry(
        profile_id=a, pillar=models.Pillar.heritage, title="A obj", is_milestone=1
    )
    db.add(obj)
    db.commit()
    gallery.link_objective(a, media.id, ObjectiveLinkCreate(objective_id=obj.id), db=db, _=admin)
    assert gallery.get_media(a, media.id, db=db).objective_ids == [obj.id]

    # Simulate age-group deactivation via the REAL objective-delete route, which
    # must clean the link but preserve the media.
    from routes import pillars

    pillars.delete_entry(a, obj.id, db=db, _=admin)

    # Media is STILL there; only the link is gone.
    survived = gallery.get_media(a, media.id, db=db)
    assert survived.id == media.id
    assert survived.objective_ids == []
    # And its bytes are still in storage.
    assert (
        storage.get_storage().read(db.query(models.ProfileMedia).get(media.id).storage_key)
        == b"JPEGDATA"
    )


def test_soft_delete_removes_from_listing_and_storage(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    media = _upload(gallery, db, a, admin)[0]
    key = db.query(models.ProfileMedia).get(media.id).storage_key
    gallery.delete_media(a, media.id, db=db, _=admin)
    assert gallery.list_gallery(a, db=db) == []
    assert storage.get_storage().read(key) is None  # bytes removed
    with pytest.raises(HTTPException):
        gallery.get_media(a, media.id, db=db)  # 404 after soft delete


def test_reg01_legacy_event_attachment_untouched(ctx):
    """The old EventAttachment table and cascade still exist unchanged."""
    gallery, models, storage, db, a, b, admin, ro = ctx
    assert hasattr(models, "EventAttachment")
    cols = {c.name for c in models.EventAttachment.__table__.columns}
    assert {"entry_id", "filename", "mime_type"} <= cols


def test_unsupported_mime_rejected(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    with pytest.raises(HTTPException) as e:
        _upload(gallery, db, a, admin, name="x.exe", mime="application/x-msdownload")
    assert e.value.status_code == 400


# --- Direct-to-storage upload (initiate -> PUT -> finalize) ------------------


def test_direct_upload_initiate_finalize_happy_path(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import UploadFinalizeRequest, UploadInitiateRequest

    init = gallery.initiate_upload(
        a,
        UploadInitiateRequest(filename="clip.mp4", content_type="video/mp4", size_bytes=5_000_000),
        db=db,
        current_user=admin,
    )
    assert init.media_id and init.upload_url and init.storage_key
    # Row exists but is PENDING and not yet listed.
    assert gallery.list_gallery(a, db=db) == []
    # Simulate the browser PUT landing in storage.
    storage.get_storage().save(init.storage_key, b"\x00" * 1000, "video/mp4")
    out = gallery.finalize_upload(
        a, init.media_id, UploadFinalizeRequest(observation="first swim"), db=db, _=admin
    )
    assert out.status == "ready" and out.media_type == "video" and out.observation == "first swim"
    assert [m.id for m in gallery.list_gallery(a, db=db)] == [init.media_id]


def test_up01_forged_finalize_before_put_is_rejected(ctx):
    """AUTH/UP-01: finalizing before the object exists must NOT mark it ready."""
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import UploadFinalizeRequest, UploadInitiateRequest

    init = gallery.initiate_upload(
        a,
        UploadInitiateRequest(filename="clip.mp4", content_type="video/mp4", size_bytes=1000),
        db=db,
        current_user=admin,
    )
    # No PUT happened; finalize must 409 and NOT list the media.
    with pytest.raises(HTTPException) as e:
        gallery.finalize_upload(a, init.media_id, UploadFinalizeRequest(), db=db, _=admin)
    assert e.value.status_code == 409
    assert gallery.list_gallery(a, db=db) == []


def test_direct_upload_oversize_rejected_at_initiate(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    import pydantic

    from schemas import MAX_DIRECT_UPLOAD_BYTES, UploadInitiateRequest

    with pytest.raises(pydantic.ValidationError):
        UploadInitiateRequest(
            filename="huge.mp4", content_type="video/mp4", size_bytes=MAX_DIRECT_UPLOAD_BYTES + 1
        )


def test_direct_upload_cross_profile_finalize_denied(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import UploadFinalizeRequest, UploadInitiateRequest

    init = gallery.initiate_upload(
        a,
        UploadInitiateRequest(filename="c.mp4", content_type="video/mp4", size_bytes=1000),
        db=db,
        current_user=admin,
    )
    storage.get_storage().save(init.storage_key, b"x", "video/mp4")
    # Finalize A's upload while scoped to B -> 404.
    with pytest.raises(HTTPException) as e:
        gallery.finalize_upload(b, init.media_id, UploadFinalizeRequest(), db=db, _=admin)
    assert e.value.status_code == 404


def test_direct_upload_bad_mime_rejected_at_initiate(ctx):
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import UploadInitiateRequest

    with pytest.raises(HTTPException) as e:
        gallery.initiate_upload(
            a,
            UploadInitiateRequest(
                filename="x.exe", content_type="application/x-msdownload", size_bytes=10
            ),
            db=db,
            current_user=admin,
        )
    assert e.value.status_code == 400


def test_age_group_deactivation_preserves_gallery_media(ctx):
    """Spec archive-loss case: deactivating a Child Development age group deletes
    its objective rows but must NOT delete canonical gallery media."""
    gallery, models, storage, db, a, b, admin, ro = ctx
    from routes import child_development as cd
    from schemas import ObjectiveLinkCreate

    # Create a CD objective in a real age band and link a gallery photo to it.
    # CD objectives are identified by a category prefixed "child_development:".
    band = next(iter(cd.AGE_GROUPS))
    obj = models.PillarEntry(
        profile_id=a,
        pillar=models.Pillar.life_skills,
        title="CD objective",
        age_band=band,
        category="child_development:social",
        is_milestone=1,
    )
    db.add(obj)
    db.commit()
    media = _upload(gallery, db, a, admin, name="accomplishment.jpg")[0]
    gallery.link_objective(a, media.id, ObjectiveLinkCreate(objective_id=obj.id), db=db, _=admin)
    key = db.query(models.ProfileMedia).get(media.id).storage_key
    obj_id = obj.id

    # Deactivate the age group (the historically destructive path).
    cd.deactivate_age_group(a, band, db=db, _=admin)

    # Objective gone, link gone, but media + bytes survive.
    assert db.query(models.PillarEntry).filter(models.PillarEntry.id == obj_id).first() is None
    survived = gallery.get_media(a, media.id, db=db)
    assert survived.objective_ids == []
    assert storage.get_storage().read(key) == b"JPEGDATA"


def test_objective_linked_media_shows_in_main_gallery_and_filtered(ctx):
    """A photo added on an objective appears in the main (unfiltered) gallery AND
    when filtered by that objective — the 'one canonical gallery' invariant."""
    gallery, models, storage, db, a, b, admin, ro = ctx
    from schemas import ObjectiveLinkCreate

    obj = models.PillarEntry(
        profile_id=a, pillar=models.Pillar.life_skills, title="obj", is_milestone=1
    )
    db.add(obj)
    db.commit()
    media = _upload(gallery, db, a, admin, name="goal.jpg")[0]
    gallery.link_objective(a, media.id, ObjectiveLinkCreate(objective_id=obj.id), db=db, _=admin)

    # Main gallery (unfiltered) shows it.
    all_ids = [m.id for m in gallery.list_gallery(a, db=db)]
    assert media.id in all_ids
    # Filtered by the objective shows exactly it.
    filtered = gallery.list_gallery(a, objective_id=obj.id, db=db)
    assert [m.id for m in filtered] == [media.id]
    # Filtered by a different objective shows nothing.
    assert gallery.list_gallery(a, objective_id=obj.id + 999, db=db) == []
