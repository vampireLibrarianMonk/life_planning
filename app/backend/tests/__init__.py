"""Backend unit-test suite (pytest).

Modular by concern so tests don't pile into one file:

  test_config_mode.py     — the DEPLOY_MODE local/aws switch in config.py
  test_storage.py         — the LocalStorage/S3Storage abstraction
  test_auth_hardening.py  — JWT + admin-credential hardening behavior
  test_health.py          — /api/health reports the active mode

This Python suite is independent of the frontend Playwright e2e/a11y suite in
app/frontend/tests; the two use different runners and never share state.
"""
