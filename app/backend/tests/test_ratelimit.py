"""TODO-9: shared rate limiter."""

import pytest
from fastapi import HTTPException


def test_throttle_raises_after_max():
    import ratelimit

    ratelimit._hits.clear()
    for _ in range(5):
        ratelimit.throttle("t:1.2.3.4", 5, 300)
    with pytest.raises(HTTPException) as e:
        ratelimit.throttle("t:1.2.3.4", 5, 300)
    assert e.value.status_code == 429


def test_throttle_is_per_key():
    import ratelimit

    ratelimit._hits.clear()
    for _ in range(5):
        ratelimit.throttle("t:a", 5, 300)
    # a different key is unaffected
    ratelimit.throttle("t:b", 5, 300)  # should not raise


def test_rate_limit_dependency_blocks_by_ip():
    import ratelimit

    ratelimit._hits.clear()
    dep = ratelimit.rate_limit("archive", 2, 300)

    class _C:
        host = "9.9.9.9"

    class _Req:
        client = _C()

    req = _Req()
    dep(req)
    dep(req)
    with pytest.raises(HTTPException) as e:
        dep(req)
    assert e.value.status_code == 429
