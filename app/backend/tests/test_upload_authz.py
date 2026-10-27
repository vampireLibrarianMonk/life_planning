"""Security regression: the /api/uploads blob route is AUTHORIZED.

Before the fix, /api/uploads/{filename} served any attachment/avatar with zero
auth — a readonly grandparent or a second child could fetch another child's
photos by filename. These tests assert the route now requires a valid token and
scopes to the owning profile (unknown/unauthorized/bad-token -> 404, no oracle).

Calls the route function directly with an in-memory DB + temp storage dir.
"""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "storage", "main", "routes.events"):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    auth = importlib.import_module("auth")
    storage = importlib.import_module("storage")
    importlib.import_module("main")
    events = importlib.import_module("routes.events")

    monkeypatch.setattr(storage, "UPLOAD_DIR", tmp_path)
    storage.get_storage.cache_clear()
    monkeypatch.setattr(storage.LocalStorage, "__init__", lambda self: None)

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    db = TestSession()

    # Two profiles. Profile A has an attachment + avatar. Child A owns A.
    pa = models.Profile(name="A", date_of_birth="2020-01-01", avatar="avatarA.png")
    pb = models.Profile(name="B", date_of_birth="2020-01-01")
    db.add_all([pa, pb])
    db.flush()
    entry = models.PillarEntry(
        profile_id=pa.id, pillar=models.Pillar.heritage, title="e", is_milestone=1
    )
    db.add(entry)
    db.flush()
    db.add(
        models.EventAttachment(
            entry_id=entry.id, filename="attA.jpg", original_name="a.jpg", mime_type="image/jpeg"
        )
    )
    child_a = models.User(
        username="childa",
        hashed_password=auth.hash_password("x" * 12),
        display_name="Child A",
        role=models.Role.child,
    )
    child_b = models.User(
        username="childb",
        hashed_password=auth.hash_password("x" * 12),
        display_name="Child B",
        role=models.Role.child,
    )
    admin = models.User(
        username="admin",
        hashed_password=auth.hash_password("x" * 12),
        display_name="Admin",
        role=models.Role.admin,
    )
    readonly = models.User(
        username="ro",
        hashed_password=auth.hash_password("x" * 12),
        display_name="RO",
        role=models.Role.readonly,
    )
    db.add_all([child_a, child_b, admin, readonly])
    db.flush()
    # Link each child to their profile (child-scoping uses Profile.user_id).
    pa.user_id = child_a.id
    pb.user_id = child_b.id
    db.commit()
    st = storage.get_storage()
    st.save("attA.jpg", b"ATTACH", "image/jpeg")
    st.save("avatarA.png", b"AVA", "image/png")

    tok = {
        u.username: auth.create_access_token({"sub": str(u.id), "role": u.role.value})
        for u in (child_a, child_b, admin, readonly)
    }
    return events, db, tok


def _serve(events, db, filename, token, cookie_token=None):
    # Minimal stand-in for a Starlette Request exposing .cookies.
    import auth as _auth

    class _Req:
        cookies = {_auth.AUTH_COOKIE_NAME: cookie_token} if cookie_token else {}

    return events.serve_upload(filename=filename, request=_Req(), token=token, db=db)


def test_no_token_is_404(ctx):
    events, db, _tok = ctx
    with pytest.raises(HTTPException) as e:
        _serve(events, db, "attA.jpg", None)
    assert e.value.status_code == 404


def test_bad_token_is_404(ctx):
    events, db, _tok = ctx
    with pytest.raises(HTTPException) as e:
        _serve(events, db, "attA.jpg", "garbage.token.here")
    assert e.value.status_code == 404


def test_cookie_token_authorizes(ctx):
    # The httpOnly cookie path must authorize identically to the query param.
    events, db, tok = ctx
    resp = _serve(events, db, "attA.jpg", token=None, cookie_token=tok["admin"])
    # Local mode -> FileResponse (has a path/status); just assert it didn't 404.
    assert getattr(resp, "status_code", 200) in (200, 307)


def test_unknown_key_is_404(ctx):
    events, db, tok = ctx
    with pytest.raises(HTTPException) as e:
        _serve(events, db, "nope.jpg", tok["admin"])
    assert e.value.status_code == 404


def test_path_escape_is_404(ctx):
    events, db, tok = ctx
    for bad in ("../secret", "a/b", "..\\x"):
        with pytest.raises(HTTPException) as e:
            _serve(events, db, bad, tok["admin"])
        assert e.value.status_code == 404


def test_owner_admin_readonly_can_fetch(ctx):
    events, db, tok = ctx
    # admin, readonly (family), and the OWNING child all succeed on A's files.
    for who in ("admin", "ro", "childa"):
        resp = _serve(events, db, "attA.jpg", tok[who])
        assert getattr(resp, "status_code", 200) in (200, 307)
        resp2 = _serve(events, db, "avatarA.png", tok[who])
        assert getattr(resp2, "status_code", 200) in (200, 307)


def test_non_owning_child_cannot_fetch_other_childs_file(ctx):
    events, db, tok = ctx
    # Child B must NOT be able to pull Child A's attachment or avatar.
    with pytest.raises(HTTPException) as e1:
        _serve(events, db, "attA.jpg", tok["childb"])
    assert e1.value.status_code == 404
    with pytest.raises(HTTPException) as e2:
        _serve(events, db, "avatarA.png", tok["childb"])
    assert e2.value.status_code == 404


def test_local_serve_forces_attachment_disposition(ctx):
    events, db, tok = ctx
    resp = _serve(events, db, "attA.jpg", tok["admin"])
    # Local mode returns a FileResponse with safe disposition + benign type.
    assert resp.headers.get("content-disposition") == "attachment"
    assert resp.media_type == "application/octet-stream"
