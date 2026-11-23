"""Regression test for the server-side Origin (CSRF) check added 2026-10-27.

The JWT is an httpOnly SameSite=strict cookie; this middleware adds a second,
server-side CSRF barrier: a cross-origin unsafe-method request with a mismatched
Origin header is rejected 403, while same-origin and header-less requests pass.
"""

import asyncio
import importlib

import pytest
from starlette.requests import Request
from starlette.responses import Response


@pytest.fixture
def app(monkeypatch):
    # This is a middleware-only test.  Do not unload/reload modules here:
    # SQLAlchemy relationship strings share one class registry for the entire
    # process, and reloading models mid-suite can split that registry.
    main = importlib.import_module("main")
    # Pin an allow-list as in AWS mode so the check is active.
    monkeypatch.setattr(main, "_allowed_origins", ["https://life-planning.my-deployment.com"])
    return main


def request(app, method, path, *, headers=None):
    """Exercise the real security middleware without a live ASGI portal.

    These tests validate middleware decisions (Origin and declared body length),
    not auth or router behavior.  A synthetic downstream response keeps them
    isolated from synchronous route/database execution.
    """
    encoded_headers = [
        (name.lower().encode(), str(value).encode()) for name, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": encoded_headers,
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def downstream(_request):
        return Response(status_code=204)

    # Keep a current loop installed: a legacy archive test below this module in
    # the suite uses get_event_loop().run_until_complete().  asyncio.run()
    # closes and unsets that loop, making otherwise-independent tests order
    # dependent on Python 3.12.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(app.security_headers(Request(scope, receive), downstream))


def test_cross_origin_post_blocked(app):
    r = request(
        app,
        "POST",
        "/api/auth/login",
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_same_origin_post_passes_csrf(app):
    # Reaches the login logic (credentials wrong -> 401, NOT 403 from CSRF).
    r = request(
        app,
        "POST",
        "/api/auth/login",
        headers={"Origin": "https://life-planning.my-deployment.com"},
    )
    assert r.status_code == 204


def test_no_origin_header_passes(app):
    r = request(app, "POST", "/api/auth/login")
    assert r.status_code == 204


def test_get_never_blocked_and_no_store(app):
    r = request(app, "GET", "/api/health")
    assert r.status_code == 204
    assert r.headers.get("cache-control") == "no-store"


# --- Request-body-size cap (regression for the gallery 413 bug) --------------


def test_gallery_route_gets_the_upload_cap_not_the_json_cap(app):
    """A multipart POST to /gallery/ with a 3MB declared length must NOT be
    rejected by the 1MB JSON cap. Before the fix /gallery/ was not in the
    upload-path allowlist, so a normal phone photo (>1MB) 413'd."""
    big = 3 * 1024 * 1024
    r = request(
        app,
        "POST",
        "/api/profiles/1/gallery/",
        headers={
            "Origin": "https://life-planning.my-deployment.com",
            "Content-Length": str(big),
            "Content-Type": "multipart/form-data; boundary=x",
        },
    )
    assert r.status_code == 204


def test_gallery_route_still_rejects_over_50mb(app):
    r = request(
        app,
        "POST",
        "/api/profiles/1/gallery/",
        headers={
            "Origin": "https://life-planning.my-deployment.com",
            "Content-Length": str(51 * 1024 * 1024),
            "Content-Type": "multipart/form-data; boundary=x",
        },
    )
    assert r.status_code == 413


def test_non_upload_route_still_has_1mb_cap(app):
    r = request(
        app,
        "POST",
        "/api/profiles/",
        headers={
            "Origin": "https://life-planning.my-deployment.com",
            "Content-Length": str(2 * 1024 * 1024),
            "Content-Type": "application/json",
        },
    )
    assert r.status_code == 413
