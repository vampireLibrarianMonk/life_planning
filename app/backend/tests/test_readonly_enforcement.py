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


# --- Child self-write lockdown (adversarial review Task 3) ------------------

CHILD_FORBIDDEN_WRITE_ROUTES = {
    # Behavior scoring feeds tier eligibility — a child must not score itself.
    ("POST", "/api/profiles/{profile_id}/incidents"),
    ("DELETE", "/api/profiles/{profile_id}/incidents/{incident_id}"),
    ("POST", "/api/profiles/{profile_id}/behavior"),
    ("PATCH", "/api/profiles/{profile_id}/behavior/{score_id}"),
}


def test_behavior_routes_are_admin_only(backend):
    """The behavior-scoring routes must be guarded by require_admin (a child
    cannot create/delete incidents or scores)."""
    main, _auth, _models = backend
    found = {}
    for route in main.app.routes:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "")
        for method in methods:
            if (method, path) in CHILD_FORBIDDEN_WRITE_ROUTES:
                found[(method, path)] = _dependency_callables(route)

    missing = CHILD_FORBIDDEN_WRITE_ROUTES - set(found)
    assert not missing, f"behavior routes not found (renamed?): {sorted(missing)}"
    offenders = [
        f"{m} {p} deps={sorted(deps)}"
        for (m, p), deps in found.items()
        if "require_admin" not in deps
    ]
    assert not offenders, "behavior routes must be admin-only:\n" + "\n".join(offenders)


def test_child_cannot_mark_bounty_paid(backend, monkeypatch):
    """update_bounty must reject status='paid' for a non-admin (child) caller
    before touching the database."""
    main, _auth, models = backend
    from routes import economy

    class _ChildUser:
        role = models.Role.child

    class _PaidReq:
        status = "paid"

    with pytest.raises(HTTPException) as exc:
        economy.update_bounty(
            profile_id=1,
            bounty_id=1,
            req=_PaidReq(),
            db=None,  # must 403 before any DB access
            current_user=_ChildUser(),
        )
    assert exc.value.status_code == 403


# --- Sensitive-read privacy (behavior log, journals, financial totals) -------

# These READ routes expose data that is private to the child + admin; family
# readonly viewers must be blocked. Paths are the registered FastAPI paths.
PRIVATE_READ_ROUTES = {
    ("GET", "/api/profiles/{profile_id}/incidents"),
    ("GET", "/api/profiles/{profile_id}/behavior"),
    ("GET", "/api/profiles/{profile_id}/earnings"),
    ("GET", "/api/profiles/{profile_id}/discernment/"),
    ("GET", "/api/profiles/{profile_id}/funds/"),
    ("GET", "/api/profiles/{profile_id}/funds/{fund_id}/transactions"),
}


def test_sensitive_reads_are_private(backend):
    """Each private read route must depend on require_private_profile_access
    (admin + the owning child only; readonly and other children blocked)."""
    main, _auth, _models = backend
    found = {}
    for route in main.app.routes:
        methods = getattr(route, "methods", None) or set()
        path = getattr(route, "path", "")
        for method in methods:
            if (method, path) in PRIVATE_READ_ROUTES:
                found[(method, path)] = _dependency_callables(route)

    missing = PRIVATE_READ_ROUTES - set(found)
    assert not missing, f"private read routes not found (renamed?): {sorted(missing)}"
    offenders = [
        f"{m} {p} deps={sorted(deps)}"
        for (m, p), deps in found.items()
        if "require_private_profile_access" not in deps
    ]
    assert not offenders, (
        "these reads must be gated by require_private_profile_access:\n" + "\n".join(offenders)
    )


def test_require_private_profile_access_role_matrix(backend):
    """require_private_profile_access: admin passes; the owning child passes; a
    non-owning child and readonly are 403'd."""
    _main, auth, models = backend

    class _Profile:
        def __init__(self, pid):
            self.id = pid

    class _U:
        def __init__(self, role, profile_pid=None):
            self.role = role
            self.profile = _Profile(profile_pid) if profile_pid is not None else None

    # admin passes for any profile
    assert auth.require_private_profile_access(
        profile_id=5, current_user=_U(models.Role.admin), db=None
    )
    # owning child passes
    assert auth.require_private_profile_access(
        profile_id=7, current_user=_U(models.Role.child, 7), db=None
    )
    # non-owning child is rejected
    with pytest.raises(HTTPException) as e1:
        auth.require_private_profile_access(
            profile_id=7, current_user=_U(models.Role.child, 99), db=None
        )
    assert e1.value.status_code == 403
    # readonly is rejected
    with pytest.raises(HTTPException) as e2:
        auth.require_private_profile_access(
            profile_id=7, current_user=_U(models.Role.readonly), db=None
        )
    assert e2.value.status_code == 403


def test_require_profile_access_blocks_cross_child(backend):
    """A child may access only their own profile; another child's is 403."""
    _main, auth, models = backend

    class _Profile:
        def __init__(self, pid):
            self.id = pid

    class _U:
        def __init__(self, role, profile_pid=None):
            self.role = role
            self.profile = _Profile(profile_pid) if profile_pid is not None else None

    # owning child ok
    assert auth.require_profile_access(profile_id=1, current_user=_U(models.Role.child, 1), db=None)
    # cross-child blocked
    with pytest.raises(HTTPException) as exc:
        auth.require_profile_access(profile_id=2, current_user=_U(models.Role.child, 1), db=None)
    assert exc.value.status_code == 403
    # admin + readonly pass for any profile
    assert auth.require_profile_access(profile_id=2, current_user=_U(models.Role.admin), db=None)
    assert auth.require_profile_access(profile_id=2, current_user=_U(models.Role.readonly), db=None)
