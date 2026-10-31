"""Regression tests for the deferred-item remediations (2026-10-27 pass 2)."""

import importlib
import sys

import pytest
from pydantic import ValidationError


@pytest.fixture
def mods(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for m in ("config", "database", "models", "auth", "main", "routes.funds"):
        sys.modules.pop(m, None)
    schemas = importlib.import_module("schemas")
    funds = importlib.import_module("routes.funds")
    return schemas, funds


# --- Numeric validation ---------------------------------------------------


def test_negative_reward_rejected(mods):
    schemas, _ = mods
    with pytest.raises(ValidationError):
        schemas.BountyUpdate(reward_amount=-100)


def test_zero_divisor_rejected(mods):
    schemas, _ = mods
    with pytest.raises(ValidationError):
        schemas.BountyCreate(tier="bronze", title="x", decay_divisor=0)


def test_behavior_score_out_of_range_rejected(mods):
    schemas, _ = mods
    with pytest.raises(ValidationError):
        schemas.BehaviorScoreCreate(week_of="2026-W01", integrity=9)


def test_negative_fund_transaction_rejected(mods):
    _, funds = mods
    with pytest.raises(ValidationError):
        funds.TransactionCreate(amount=-500, description="sneaky inflate")


def test_zero_fund_transaction_rejected(mods):
    _, funds = mods
    with pytest.raises(ValidationError):
        funds.TransactionCreate(amount=0, description="noop")


# --- JWT rotation-safe decode --------------------------------------------


def test_decode_accepts_previous_secret(monkeypatch):
    # Sign with an OLD secret, rotate current, ensure decode still accepts it
    # when the old one is provided as SECRET_KEY_PREVIOUS.
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "new-secret-" + "a" * 32)
    monkeypatch.setenv("SECRET_KEY_PREVIOUS", "old-secret-" + "b" * 32)
    for m in ("config", "auth"):
        sys.modules.pop(m, None)
    import jwt

    # Token minted under the PREVIOUS secret.
    old_token = jwt.encode(
        {"sub": "1", "role": "admin"}, "old-secret-" + "b" * 32, algorithm="HS256"
    )
    import auth

    payload = auth.decode_token(old_token)
    assert payload["sub"] == "1"


def test_decode_rejects_unknown_secret(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "the-only-valid-" + "c" * 32)
    monkeypatch.delenv("SECRET_KEY_PREVIOUS", raising=False)
    for m in ("config", "auth"):
        sys.modules.pop(m, None)
    import jwt
    from jwt import InvalidTokenError as JWTError

    import auth

    bad = jwt.encode({"sub": "1"}, "some-other-secret", algorithm="HS256")
    with pytest.raises(JWTError):
        auth.decode_token(bad)
