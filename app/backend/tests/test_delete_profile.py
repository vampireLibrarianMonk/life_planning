"""Admin delete-profile endpoint removes a profile and all its data cleanly."""

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
    profiles = importlib.import_module("routes.profiles")

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    database.Base.metadata.create_all(bind=engine)
    return profiles, models, TestSession()


class _Admin:
    role = None  # set in test from models.Role.admin


def test_delete_profile_cascades(ctx):
    profiles, models, db = ctx

    profile = models.Profile(name="Doomed", date_of_birth="2015-01-01")
    db.add(profile)
    db.flush()
    pid = profile.id

    # Nested data across several tables, incl. a parent+child PillarEntry and a
    # bounty with a log (grandchild) + a fund with a transaction (grandchild).
    parent_entry = models.PillarEntry(
        profile_id=pid, pillar=models.Pillar.spiritual, title="parent", is_milestone=1
    )
    db.add(parent_entry)
    db.flush()
    db.add(
        models.PillarEntry(
            profile_id=pid,
            pillar=models.Pillar.spiritual,
            title="child entry",
            parent_id=parent_entry.id,
        )
    )
    bounty = models.Bounty(profile_id=pid, tier=models.BountyTier.bronze, title="b")
    db.add(bounty)
    db.flush()
    db.add(models.BountyLog(bounty_id=bounty.id, author="child", content="log"))
    fund = models.Fund(profile_id=pid, name="f", starting_balance=1000)
    db.add(fund)
    db.flush()
    db.add(models.FundTransaction(fund_id=fund.id, amount=100, description="t"))
    db.add(
        models.BehaviorIncident(profile_id=pid, trait="honesty", description="x", date="2026-01-01")
    )
    db.add(models.DiscernmentJournal(profile_id=pid, category="faith", title="t", reflection="r"))
    lesson = models.LessonPlan(profile_id=pid, title="L", transcript="...")
    db.add(lesson)
    db.flush()
    db.add(models.LessonResponse(lesson_id=lesson.id, response_type="rebrief", content="c"))
    db.commit()

    admin = _Admin()
    admin.role = models.Role.admin

    # Delete via the endpoint function.
    profiles.delete_profile(profile_id=pid, db=db, _=admin)

    # Nothing left for this profile in any table.
    assert db.query(models.Profile).filter(models.Profile.id == pid).first() is None
    for model in (
        models.PillarEntry,
        models.Bounty,
        models.Fund,
        models.BehaviorIncident,
        models.DiscernmentJournal,
        models.LessonPlan,
    ):
        assert db.query(model).filter(model.profile_id == pid).count() == 0, model.__name__
    # Grandchildren gone too (via cascade).
    assert db.query(models.BountyLog).count() == 0
    assert db.query(models.FundTransaction).count() == 0
    assert db.query(models.LessonResponse).count() == 0


def test_delete_missing_profile_404(ctx):
    profiles, models, db = ctx
    admin = _Admin()
    admin.role = models.Role.admin
    with pytest.raises(HTTPException) as exc:
        profiles.delete_profile(profile_id=999, db=db, _=admin)
    assert exc.value.status_code == 404
