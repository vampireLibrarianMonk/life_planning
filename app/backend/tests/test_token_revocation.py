"""TODO-5: JWT revocation (token_version) + self-service change-password."""

import importlib
import sys

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/tv.db")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme")
    # Pop EVERY module that holds a reference to the db engine/SessionLocal so
    # they re-bind to this test's fresh DATABASE_URL (route modules do
    # `from database import ...`, so popping only `database` isn't enough).
    for m in list(sys.modules):
        if (
            m == "database"
            or m == "config"
            or m == "models"
            or m == "auth"
            or m == "main"
            or m.startswith("routes")
        ):
            sys.modules.pop(m, None)
    main = importlib.import_module("main")
    # trigger startup admin seed
    with TestClient(main.app) as c:
        yield c


def _login(c, u="admin", p="changeme"):
    return c.post(
        "/api/auth/login",
        json={"username": u, "password": p},
        headers={"Origin": "http://testserver"},
    )


def test_login_me_works(client):
    r = _login(client)
    assert r.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["username"] == "admin"


def test_logout_revokes_token(client):
    _login(client)
    # capture the cookie, then logout (bumps token_version)
    cookie = client.cookies.get("lp_auth")
    assert cookie
    client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
    # Re-present the OLD token via Authorization header — must now be rejected.
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {cookie}"})
    assert me.status_code == 401


def test_change_password_requires_current(client):
    _login(client)
    r = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong", "new_password": "newpass123"},
        headers={"Origin": "http://testserver"},
    )
    assert r.status_code == 403


def test_change_password_rotates_and_revokes_old_tokens(client):
    _login(client)
    old_cookie = client.cookies.get("lp_auth")
    r = client.post(
        "/api/auth/change-password",
        json={"current_password": "changeme", "new_password": "newpass123"},
        headers={"Origin": "http://testserver"},
    )
    assert r.status_code == 200
    # This session got a fresh cookie and still works.
    assert client.get("/api/auth/me").status_code == 200
    # Old token revoked: clear the cookie jar and re-present the OLD token as a
    # bearer header — cookie-first extract now has no cookie to prefer.
    client.cookies.clear()
    me_old = client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_cookie}"})
    assert me_old.status_code == 401
    # New password logs in; old password does not (token_version + hash changed).
    assert _login(client, p="newpass123").status_code == 200
    client.cookies.clear()
    assert _login(client, p="changeme").status_code == 401
