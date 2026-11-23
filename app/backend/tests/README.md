# Backend tests

Each test module owns one feature area. The suite adds markers from the module
name in `conftest.py`, so focused failures are fast to reproduce without
duplicating decorators on every test.

```bash
# Everything (the required release gate)
.venv/bin/python -m pytest app/backend/tests

# Focused feature suites
.venv/bin/python -m pytest app/backend/tests -m uploads
.venv/bin/python -m pytest app/backend/tests -m development
.venv/bin/python -m pytest app/backend/tests -m security
.venv/bin/python -m pytest app/backend/tests -m archive

# Fast feedback while deliberately excluding the full archive/delete/restore
# round trip. Run the integration marker before a release.
.venv/bin/python -m pytest app/backend/tests -m "not integration"
.venv/bin/python -m pytest app/backend/tests -m integration
```

`test_delete_profile.py` is the archive module. Its full round-trip case is an
explicit integration test; token and restore-hardening cases remain available
under the `archive` marker for quick diagnosis.
