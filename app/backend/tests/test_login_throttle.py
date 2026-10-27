"""Login throttle (defense-in-depth brute-force limiter)."""

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def users_mod(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "main", "routes.users"):
        sys.modules.pop(mod, None)
    importlib.import_module("main")
    users = importlib.import_module("routes.users")
    users._login_attempts.clear()
    return users


class _Req:
    def __init__(self, ip):
        class _C:
            host = ip

        self.client = _C()


class _Login:
    def __init__(self, username, password):
        self.username = username
        self.password = password


class _Resp:
    """Minimal Response stand-in (login sets a cookie on success)."""

    def set_cookie(self, *a, **k):
        pass

    def delete_cookie(self, *a, **k):
        pass


def test_login_throttles_after_max_attempts(users_mod, monkeypatch):
    users = users_mod
    # No DB needed: the throttle fires before any DB access once the cap is hit.
    req = _Login("victim", "wrong")
    http = _Req("203.0.113.9")

    # First _LOGIN_MAX_ATTEMPTS calls should get PAST the throttle (and then fail
    # on credentials — a 401 — because there's no such user). We only assert the
    # throttle boundary: the (max+1)th call raises 429 before credential checks.
    calls = 0
    last_status = None
    for _ in range(users._LOGIN_MAX_ATTEMPTS + 3):
        try:
            users.login(req=req, request=http, response=_Resp(), db=_FakeDB())
        except HTTPException as e:
            last_status = e.value if False else e.status_code
        calls += 1
        if last_status == 429:
            break
    assert last_status == 429, "expected a 429 once the attempt cap is exceeded"


def test_throttle_is_per_ip_username_key(users_mod):
    users = users_mod
    # Exhaust one key; a different IP/username key is unaffected.
    k1 = "1.1.1.1:userA"
    for _ in range(users._LOGIN_MAX_ATTEMPTS):
        users._login_throttle(k1)
    with pytest.raises(HTTPException) as e:
        users._login_throttle(k1)
    assert e.value.status_code == 429
    # Different key still allowed.
    users._login_throttle("2.2.2.2:userB")  # should not raise


class _FakeDB:
    """Minimal DB stub: query(...).filter(...).first() -> None (no such user)."""

    def query(self, *a, **k):
        return self

    def filter(self, *a, **k):
        return self

    def first(self):
        return None
