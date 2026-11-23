"""JWT revocation and self-service password-change behavior.

These tests call route functions rather than starting Starlette's TestClient
lifespan. The behavior under test is database and token state, not ASGI
transport; this avoids an AnyIO lifecycle hang obscuring backend failures.
"""

import importlib
import sys
from http.cookies import SimpleCookie

import pytest
from fastapi import HTTPException
from starlette.responses import Response


@pytest.fixture
def auth_ctx(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/tv.db")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "changeme")
    # Route modules retain imported model/database references. Reload them all
    # against this test's private SQLite database.
    for module in list(sys.modules):
        if module in {
            "database",
            "config",
            "models",
            "auth",
            "storage",
            "main",
        } or module.startswith("routes"):
            sys.modules.pop(module, None)

    main = importlib.import_module("main")
    database = importlib.import_module("database")
    models = importlib.import_module("models")
    auth = importlib.import_module("auth")
    users = importlib.import_module("routes.users")
    main.seed_admin()
    db = database.SessionLocal()
    try:
        yield auth, users, models, db
    finally:
        db.close()


class _Client:
    host = "127.0.0.1"


class _LoginRequest:
    def __init__(self):
        self.client = _Client()


class _CookieRequest:
    def __init__(self, token):
        self.cookies = {"lp_auth": token}


def _cookie_value(response, name="lp_auth"):
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie[name].value


def _login(users, db, username="admin", password="changeme"):
    response = Response()
    users.login(
        req=users.LoginRequest(username=username, password=password),
        request=_LoginRequest(),
        response=response,
        db=db,
    )
    return _cookie_value(response)


def test_login_me_works(auth_ctx):
    auth, users, _models, db = auth_ctx
    token = _login(users, db)
    assert auth.get_current_user(token=token, db=db).username == "admin"


def test_logout_revokes_token(auth_ctx):
    auth, users, _models, db = auth_ctx
    token = _login(users, db)
    users.logout(request=_CookieRequest(token), response=Response(), db=db)
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(token=token, db=db)
    assert exc.value.status_code == 401


def test_change_password_requires_current_password(auth_ctx):
    auth, users, _models, db = auth_ctx
    token = _login(users, db)
    current_user = auth.get_current_user(token=token, db=db)
    with pytest.raises(HTTPException) as exc:
        users.change_password(
            req=users.ChangePasswordRequest(current_password="wrong", new_password="newpass123"),
            response=Response(),
            current_user=current_user,
            db=db,
        )
    assert exc.value.status_code == 403


def test_change_password_rotates_and_revokes_old_tokens(auth_ctx):
    auth, users, _models, db = auth_ctx
    old_token = _login(users, db)
    response = Response()
    users.change_password(
        req=users.ChangePasswordRequest(current_password="changeme", new_password="newpass123"),
        response=response,
        current_user=auth.get_current_user(token=old_token, db=db),
        db=db,
    )
    new_token = _cookie_value(response)
    assert auth.get_current_user(token=new_token, db=db).username == "admin"
    with pytest.raises(HTTPException) as exc:
        auth.get_current_user(token=old_token, db=db)
    assert exc.value.status_code == 401

    assert _login(users, db, password="newpass123")
    with pytest.raises(HTTPException) as exc:
        _login(users, db, password="changeme")
    assert exc.value.status_code == 401
