"""Lightweight in-process sliding-window rate limiter.

Shared by the login throttle and the expensive-endpoint guards. Process-local
(App Runner is pinned to a single instance), so it resets on redeploy — it's
defense-in-depth that complements the WAF rate rule, not a distributed limiter.
No external deps.
"""

import time

from fastapi import HTTPException

# One shared store keyed by "<bucket>:<identity>"; values are hit timestamps.
_hits: dict[str, list[float]] = {}


def throttle(key: str, max_hits: int, window_seconds: int, detail: str | None = None) -> None:
    """Record a hit for `key`; raise 429 if it exceeds max_hits in the window."""
    now = time.monotonic()
    cutoff = now - window_seconds
    recent = [t for t in _hits.get(key, []) if t > cutoff]
    if len(recent) >= max_hits:
        raise HTTPException(
            status_code=429,
            detail=detail or "Too many requests. Please wait and try again.",
        )
    recent.append(now)
    _hits[key] = recent
    # Opportunistic cleanup so the dict can't grow unbounded.
    if len(_hits) > 2000:
        for k in [k for k, v in _hits.items() if not any(t > cutoff for t in v)]:
            _hits.pop(k, None)


def rate_limit(bucket: str, max_hits: int, window_seconds: int):
    """FastAPI dependency factory: throttle by client IP for `bucket`.

    Usage: `_rl = Depends(rate_limit("archive", 5, 300))` on a route, or in the
    route's `dependencies=[...]`.
    """
    from fastapi import Request

    def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        throttle(
            f"{bucket}:{ip}",
            max_hits,
            window_seconds,
            detail=f"Too many '{bucket}' requests. Please wait a few minutes.",
        )

    return _dep
