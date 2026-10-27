"""Regression tests for the 2026-10-27 panel findings (economy integrity + IDOR).

- C1: a CHILD must not be able to PATCH money/counter fields on a bounty
  (reward_amount, times_completed, streak_count, decay_divisor, ...).
- H2: list_bounty_logs must be scoped to the owning profile (no cross-profile
  IDOR via a global bounty_id).
"""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def ctx(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "main", "routes.economy"):
        sys.modules.pop(mod, None)
    models = importlib.import_module("models")
    importlib.import_module("auth")
    database = importlib.import_module("database")
    economy = importlib.import_module("routes.economy")

    # Fresh in-memory-ish DB
    database.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    return economy, models, db


def _mk_user(models, role, uid, profile_id=None):
    class _U:
        pass

    u = _U()
    u.id = uid
    u.role = role
    u.profile = None
    if profile_id is not None:

        class _P:
            id = profile_id

        u.profile = _P()
    return u


def _seed_bounty(models, db, profile_id, reward=500):
    b = models.Bounty(
        profile_id=profile_id,
        tier="bronze",
        title="Test bounty",
        reward_amount=reward,
        status="available",
        repeatable=0,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def test_child_cannot_mass_assign_money_fields(ctx):
    economy, models, db = ctx
    b = _seed_bounty(models, db, profile_id=1, reward=500)
    child = _mk_user(models, models.Role.child, uid=6, profile_id=1)

    # Child tries to inflate the reward — must be rejected 403, value unchanged.
    req = economy.BountyUpdate(reward_amount=5_000_000)
    with pytest.raises(HTTPException) as e:
        economy.update_bounty(profile_id=1, bounty_id=b.id, req=req, db=db, current_user=child)
    assert e.value.status_code == 403
    db.refresh(b)
    assert b.reward_amount == 500  # untouched

    # times_completed / streak_count likewise forbidden.
    with pytest.raises(HTTPException) as e2:
        economy.update_bounty(
            profile_id=1,
            bounty_id=b.id,
            req=economy.BountyUpdate(times_completed=52, streak_count=52),
            db=db,
            current_user=child,
        )
    assert e2.value.status_code == 403


def test_child_may_still_claim_and_complete(ctx):
    economy, models, db = ctx
    b = _seed_bounty(models, db, profile_id=1)
    child = _mk_user(models, models.Role.child, uid=6, profile_id=1)
    economy.update_bounty(
        profile_id=1,
        bounty_id=b.id,
        req=economy.BountyUpdate(status="claimed"),
        db=db,
        current_user=child,
    )
    db.refresh(b)
    assert b.status == "claimed"


def test_child_cannot_set_paid(ctx):
    economy, models, db = ctx
    b = _seed_bounty(models, db, profile_id=1)
    child = _mk_user(models, models.Role.child, uid=6, profile_id=1)
    with pytest.raises(HTTPException) as e:
        economy.update_bounty(
            profile_id=1,
            bounty_id=b.id,
            req=economy.BountyUpdate(status="paid"),
            db=db,
            current_user=child,
        )
    assert e.value.status_code == 403


def test_bounty_logs_scoped_to_profile(ctx):
    economy, models, db = ctx
    # Bounty belongs to profile 2; a request under profile 1's path must 404.
    b = _seed_bounty(models, db, profile_id=2)
    viewer = _mk_user(models, models.Role.readonly, uid=5)
    with pytest.raises(HTTPException) as e:
        economy.list_bounty_logs(profile_id=1, bounty_id=b.id, db=db, _=viewer)
    assert e.value.status_code == 404
    # Correct profile path works (returns a list).
    out = economy.list_bounty_logs(profile_id=2, bounty_id=b.id, db=db, _=viewer)
    assert isinstance(out, list)
