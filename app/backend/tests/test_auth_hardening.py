"""Tests for auth + admin-credential hardening.

Covers bcrypt round-trip, JWT create/verify, and the AWS-mode guard that
refuses the default admin credential.
"""

import importlib
import sys


def _fresh_auth(monkeypatch, **env):
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    for mod in ("config", "auth"):
        sys.modules.pop(mod, None)
    return importlib.import_module("auth")


def test_bcrypt_hash_roundtrip(monkeypatch):
    auth = _fresh_auth(monkeypatch, DEPLOY_MODE="local", SECRET_KEY="x" * 40)
    hashed = auth.hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert auth.verify_password("correct horse battery staple", hashed) is True
    assert auth.verify_password("wrong", hashed) is False


def test_jwt_create_and_decode(monkeypatch):
    auth = _fresh_auth(monkeypatch, DEPLOY_MODE="local", SECRET_KEY="y" * 40)
    from jose import jwt

    token = auth.create_access_token({"sub": "1", "role": "admin"})
    payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    assert payload["sub"] == "1"
    assert payload["role"] == "admin"


def test_aws_mode_rejects_default_admin(monkeypatch):
    """The startup guard must refuse admin/changeme in AWS mode.

    We simulate the guard condition directly (the real check lives in main.py's
    startup hook) to prove the policy without standing up the app.
    """
    sys.modules.pop("config", None)
    monkeypatch.setenv("DEPLOY_MODE", "aws")
    config = importlib.import_module("config")

    # In AWS mode with no secret ARN, fetching creds must raise (never silently
    # fall back to admin/changeme).
    monkeypatch.delenv("ADMIN_SECRET_ARN", raising=False)
    try:
        config.get_admin_credentials()
        raise AssertionError("AWS mode must not fall back to default admin creds")
    except RuntimeError:
        pass
