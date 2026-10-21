"""Regression guard: readonly users must be denied EVERY write route.

Rationale (adversarial review, 2026-10-21): readonly write-blocking is
currently incidental — it falls out of `require_admin_or_child` rejecting a
role that is neither admin nor child, while the explicit `require_write_access`
guard is defined but unused. If someone later adds a write route wired to a
non-blocking dependency (e.g. bare `get_current_user`), readonly could silently
gain write access. This test enumerates the live route table and asserts that
every mutating route depends on a guard that rejects readonly, so such a
regression fails CI instead of shipping.

This intentionally avoids the HTTP TestClient (which needs httpx, not a runtime
dependency) and instead inspects each route's dependency callables directly,
then proves those guards raise 403 for a readonly user.
"""

import importlib
import sys

import pytest
from fastapi import HTTPException

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Public/pre-session auth routes — not "write access" in the role sense.
EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/setup",  # public: new user sets their own password via token
}


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("DEPLOY_MODE", "local")
    monkeypatch.setenv("SECRET_KEY", "z" * 40)
    for mod in ("config", "database", "models", "auth", "main"):
        sys.modules.pop(mod, None)
    models = importlib.import_module("models")
    auth = importlib.import_module("auth")
    main = importlib.import_module("main")
    return main, auth, models


def _dependency_callables(route):
    """Return the set of dependency callables attached to a route."""
    names = set()
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return names
    stack = [dependant]
    while stack:
        dep = stack.pop()
        call = getattr(dep, "call", None)
        if call is not None:
            names.add(getattr(call, "__name__", str(call)))
        stack.extend(getattr(dep, "dependencies", []))
    return names


def test_every_write_route_uses_a_role_guard(backend):
    """Each mutating /api route must depend on a guard that excludes readonly."""
    main, _auth, _models = backend
    # Guards that are known to reject a readonly role.
    blocking_guards = {"require_admin", "require_admin_or_child", "require_write_access"}

    offenders = []
    checked = 0
    for route in main.app.routes:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "")
        if not path.startswith("/api/") or path in EXEMPT_PATHS:
            continue
        if not (methods & WRITE_METHODS):
            continue
        checked += 1
        guards = _dependency_callables(route)
        if not (guards & blocking_guards):
            offenders.append(f"{sorted(methods & WRITE_METHODS)} {path} deps={sorted(guards)}")

    assert checked > 0, "no write routes discovered — enumeration is broken"
    assert not offenders, (
        "these write routes are NOT protected by a readonly-blocking guard:\n"
        + "\n".join(offenders)
    )


def test_guards_actually_reject_readonly(backend):
    """Prove the role guards raise 403 for a readonly user (not just named)."""
    _main, auth, models = backend

    class _ROUser:
        role = models.Role.readonly

    ro = _ROUser()
    for guard_name in ("require_admin", "require_admin_or_child"):
        guard = getattr(auth, guard_name)
        with pytest.raises(HTTPException) as exc:
            guard(current_user=ro)
        assert exc.value.status_code == 403, f"{guard_name} did not 403 readonly"
