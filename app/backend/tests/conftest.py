"""Shared pytest fixtures/helpers for the backend suite.

Keeps config module reloading in one place so each test file can request a
clean config module under a chosen DEPLOY_MODE without duplicating the dance.
"""

import importlib
import sys

import pytest


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
