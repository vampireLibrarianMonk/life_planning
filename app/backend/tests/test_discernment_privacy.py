"""Discernment journal = the child's private diary (authorship rules).

Rules under test (owner spec 2026-10-21):
  - Entries carry an author (created_by: 'child' | 'admin').
  - A CHILD sees every entry on their profile (own reflections + parent notes).
  - An ADMIN sees ONLY admin-authored entries — never the child's private
    reflections.
  - edit/delete is restricted to the author's own role (admin can't touch the
    child's reflections and vice-versa).

Calls the route functions directly (no HTTP TestClient, which would need httpx
that isn't a runtime dependency), matching the style of the other backend tests.
"""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "main"):
        sys.modules.pop(mod, None)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    database = importlib.import_module("database")
    models = importlib.import_module("models")
    importlib.import_module("main")  # registers models/metadata
    discernment = importlib.import_module("routes.discernment")

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    db = TestSession()

    profile = models.Profile(name="Kid", date_of_birth="2015-01-01")
    db.add(profile)
    db.flush()
    pid = profile.id

    class _U:
        def __init__(self, role):
            self.role = role

    child = _U(models.Role.child)
    admin = _U(models.Role.admin)
    return discernment, db, pid, child, admin


def test_journal_authorship_and_visibility(ctx):
    disc, db, pid, child, admin = ctx

    # Child writes a private reflection; admin writes a parent note.
    child_entry = disc.create_entry(
        profile_id=pid,
        req=disc.JournalCreate(category="faith", title="mine", reflection="secret"),
        db=db,
        current_user=child,
    )
    assert child_entry.created_by == "child"

    admin_entry = disc.create_entry(
        profile_id=pid,
        req=disc.JournalCreate(category="faith", title="note", reflection="parent obs"),
        db=db,
        current_user=admin,
    )
    assert admin_entry.created_by == "admin"

    # Child sees BOTH (own reflection + parent note).
    child_view = disc.list_entries(profile_id=pid, category=None, db=db, current_user=child)
    assert {e.id for e in child_view} == {child_entry.id, admin_entry.id}

    # Admin sees ONLY the admin note — never the child's private reflection.
    admin_view = disc.list_entries(profile_id=pid, category=None, db=db, current_user=admin)
    assert {e.id for e in admin_view} == {admin_entry.id}

    # Admin cannot edit/delete the child's reflection.
    with pytest.raises(HTTPException) as e1:
        disc.update_entry(
            profile_id=pid,
            entry_id=child_entry.id,
            req=disc.JournalUpdate(title="hax"),
            db=db,
            current_user=admin,
        )
    assert e1.value.status_code == 403
    with pytest.raises(HTTPException) as e2:
        disc.delete_entry(profile_id=pid, entry_id=child_entry.id, db=db, current_user=admin)
    assert e2.value.status_code == 403

    # Child cannot edit/delete the admin's note.
    with pytest.raises(HTTPException) as e3:
        disc.update_entry(
            profile_id=pid,
            entry_id=admin_entry.id,
            req=disc.JournalUpdate(title="x"),
            db=db,
            current_user=child,
        )
    assert e3.value.status_code == 403

    # Each may modify their own.
    updated = disc.update_entry(
        profile_id=pid,
        entry_id=child_entry.id,
        req=disc.JournalUpdate(title="edited"),
        db=db,
        current_user=child,
    )
    assert updated.title == "edited"
    disc.delete_entry(profile_id=pid, entry_id=admin_entry.id, db=db, current_user=admin)
    remaining = disc.list_entries(profile_id=pid, category=None, db=db, current_user=child)
    assert {e.id for e in remaining} == {child_entry.id}
