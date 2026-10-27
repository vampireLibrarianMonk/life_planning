"""Regression test for the server-side Origin (CSRF) check added 2026-10-27.

The JWT is an httpOnly SameSite=strict cookie; this middleware adds a second,
server-side CSRF barrier: a cross-origin unsafe-method request with a mismatched
Origin header is rejected 403, while same-origin and header-less requests pass.
"""

import importlib
import sys

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for m in ("config", "database", "models", "auth", "main"):
        sys.modules.pop(m, None)
    main = importlib.import_module("main")
    # Pin an allow-list as in AWS mode so the check is active.
    main._allowed_origins = ["https://life-planning.my-deployment.com"]
    return TestClient(main.app)


def test_cross_origin_post_blocked(client):
    r = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "x"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_same_origin_post_passes_csrf(client):
    # Reaches the login logic (credentials wrong -> 401, NOT 403 from CSRF).
    r = client.post(
        "/api/auth/login",
        json={"username": "nobody", "password": "x"},
        headers={"Origin": "https://life-planning.my-deployment.com"},
    )
    assert r.status_code == 401


def test_no_origin_header_passes(client):
    r = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_get_never_blocked_and_no_store(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers.get("cache-control") == "no-store"
