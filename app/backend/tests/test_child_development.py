"""Child Development section — backend behavior + access guards.

Covers: seed (idempotent) an age group, overview/active tracking, grouped
age-group read, deactivate, the family-readable vs. parent-only-worries split,
and exclusion of CD rows from the normal pillar entry listing. Calls route
functions directly (no httpx needed), matching the other backend tests.
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
    importlib.import_module("main")
    cd = importlib.import_module("routes.child_development")
    pillars = importlib.import_module("routes.pillars")

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    db = TestSession()
    profile = models.Profile(name="Kid", date_of_birth="2025-01-01")
    db.add(profile)
    db.commit()
    return cd, pillars, models, db, profile.id


class _U:
    def __init__(self, role):
        self.role = role


def _admin(models):
    return _U(models.Role.admin)


def _child(models, pid):
    u = _U(models.Role.child)

    class _P:
        id = pid

    u.profile = _P()
    return u


def _readonly(models):
    return _U(models.Role.readonly)


def test_seed_is_idempotent_and_grouped(ctx):
    cd, _pillars, models, db, pid = ctx
    admin = _admin(models)

    r1 = cd.seed_age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    assert r1["created"] > 0
    first = r1["created"]

    # Re-seeding creates nothing new (idempotent).
    r2 = cd.seed_age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    assert r2["created"] == 0
    assert r2["already_present"] == first

    # Overview shows 12mo active, others not.
    ov = cd.overview(profile_id=pid, db=db, _=admin)
    assert "12mo" in ov["active"]
    assert any(c["age_band"] == "12mo" and c["active"] for c in ov["catalog"])
    assert any(c["age_band"] == "2mo" and not c["active"] for c in ov["catalog"])

    # Age-group read is grouped by all 5 domains and non-empty.
    grp = cd.age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    assert set(grp["objectives"].keys()) == set(cd.DOMAINS.keys())
    total = sum(len(v) for v in grp["objectives"].values())
    assert total == first
    # Each objective has the tri-state-mappable default status.
    for items in grp["objectives"].values():
        for it in items:
            assert it["status"] == "not_started"


def test_unknown_age_group_404(ctx):
    cd, _pillars, models, db, pid = ctx
    with pytest.raises(HTTPException) as e:
        cd.seed_age_group(profile_id=pid, age_band="99mo", db=db, _=_admin(models))
    assert e.value.status_code == 404


def test_deactivate_removes_rows(ctx):
    cd, _pillars, models, db, pid = ctx
    admin = _admin(models)
    cd.seed_age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    cd.deactivate_age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    ov = cd.overview(profile_id=pid, db=db, _=admin)
    assert "12mo" not in ov["active"]
    grp = cd.age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    assert sum(len(v) for v in grp["objectives"].values()) == 0


def test_cd_rows_excluded_from_normal_pillar_list(ctx):
    cd, pillars, models, db, pid = ctx
    admin = _admin(models)
    cd.seed_age_group(profile_id=pid, age_band="12mo", db=db, _=admin)
    # A normal education-pillar entry should still appear...
    from schemas import Pillar

    normal = pillars.create_entry(
        profile_id=pid,
        req=importlib.import_module("schemas").PillarEntryCreate(
            pillar=Pillar.education, title="Normal edu milestone", is_milestone=1
        ),
        db=db,
        _=admin,
    )
    listed = pillars.list_entries(
        profile_id=pid,
        pillar=Pillar.education,
        parent_id=None,
        top_level=True,
        db=db,
        current_user=admin,
    )
    titles = {e.title for e in listed}
    assert "Normal edu milestone" in titles
    # ...but NONE of the Child Development objectives leak into the pillar view.
    assert not any((e.category or "").startswith("child_development") for e in listed)
    assert normal.id is not None


def test_worries_private_split(ctx):
    cd, _pillars, models, db, pid = ctx
    admin = _admin(models)
    child = _child(models, pid)
    readonly = _readonly(models)

    # Admin writes a private worry.
    cd.set_worries(
        profile_id=pid,
        age_band="12mo",
        req=cd.WorriesUpdate(content="late walker?"),
        db=db,
        current_user=admin,
    )
    # Admin + owning child can read it.
    assert (
        cd.get_worries(profile_id=pid, age_band="12mo", db=db, _=admin)["content"] == "late walker?"
    )
    assert (
        cd.get_worries(profile_id=pid, age_band="12mo", db=db, _=child)["content"] == "late walker?"
    )

    # The worries row must NOT be family-readable: it is not a
    # 'child_development:<domain>' objective, so it never appears in objectives.
    grp = cd.age_group(profile_id=pid, age_band="12mo", db=db, _=readonly)
    for items in grp["objectives"].values():
        assert all("worr" not in (i["title"].lower()) for i in items)


def test_require_private_profile_access_blocks_readonly(ctx):
    # The route depends on require_private_profile_access; prove that guard 403s
    # a readonly user (the worries note is parent/child-only).
    cd, _pillars, models, db, pid = ctx
    import auth

    with pytest.raises(HTTPException) as e:
        auth.require_private_profile_access(profile_id=pid, current_user=_readonly(models), db=db)
    assert e.value.status_code == 403
