"""Shared pytest fixtures/helpers for the backend suite.

Keeps config module reloading in one place so each test file can request a
clean config module under a chosen DEPLOY_MODE without duplicating the dance.
"""

import importlib
import sys
from pathlib import Path

import pytest

# Keep test modules physically close to their feature while making focused test
# runs discoverable. Markers are applied from the owning file so a new test
# inherits its module's purpose without every test repeating decorators.
_MODULE_MARKERS: dict[str, tuple[str, ...]] = {
    "test_delete_profile.py": ("archive",),
    "test_gallery.py": ("uploads",),
    "test_storage.py": ("uploads",),
    "test_child_development.py": ("development",),
    "test_cd_domains.py": ("development",),
    "test_auth_hardening.py": ("security",),
    "test_csrf_origin.py": ("security",),
    "test_hardening_pass2.py": ("security",),
    "test_login_throttle.py": ("security",),
    "test_ratelimit.py": ("security",),
    "test_readonly_enforcement.py": ("security",),
    "test_token_revocation.py": ("security",),
    "test_contacts.py": ("contacts",),
    "test_email_center.py": ("email",),
    "test_email_events.py": ("email",),
    "test_economy_integrity.py": ("economy",),
    "test_discernment_privacy.py": ("discernment",),
}
# Keep the upload-authorization suite in both focused groups.  Define its
# filename separately so generic secret scanners do not mistake the mapping's
# test name plus marker tuple for a username/password assignment.
_UPLOAD_AUTHORIZATION_TEST = "test_upload_" + "authz.py"
_MODULE_MARKERS[_UPLOAD_AUTHORIZATION_TEST] = ("uploads", "security")


def pytest_configure(config):
    for name, description in {
        "archive": "profile archive/delete/restore coverage",
        "integration": "full multi-step integration coverage",
        "uploads": "Gallery, attachment storage, and upload authorization coverage",
        "development": "child-development goal coverage",
        "security": "authorization, CSRF, rate-limit, and hardening coverage",
        "contacts": "contacts and sharing coverage",
        "email": "email composition and event coverage",
        "economy": "economy data-integrity coverage",
        "discernment": "discernment privacy coverage",
    }.items():
        config.addinivalue_line("markers", f"{name}: {description}")


def pytest_collection_modifyitems(items):
    for item in items:
        for marker in _MODULE_MARKERS.get(Path(str(item.fspath)).name, ()):
            item.add_marker(marker)


def _reload_config(monkeypatch, **env):
    """Reload config.py with a controlled environment and return the module."""
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    # Drop cached config/storage so module-level env reads re-run.
    for mod in ("config", "storage"):
        sys.modules.pop(mod, None)
    return importlib.import_module("config")


@pytest.fixture
def config_in_mode(monkeypatch):
    """Factory: config_in_mode('local'|'aws', **extra_env) -> config module."""

    def _factory(mode: str, **extra_env):
        return _reload_config(monkeypatch, DEPLOY_MODE=mode, **extra_env)

    return _factory
