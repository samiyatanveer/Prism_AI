"""Small fail-closed, process-local rate limiter for sensitive endpoints.

Redis remains available for deployment-wide caching/coordination, but this
limiter deliberately has no external dependency: if Redis is unavailable, the
authentication and credential endpoints must still be protected.
"""

from collections import defaultdict, deque
from time import monotonic

from fastapi import Request

_WINDOW_SECONDS = 60.0
_LIMITS = {"auth": 20, "assistant": 30, "exchange": 20}
_requests: dict[str, deque[float]] = defaultdict(deque)


def sensitive_endpoint_group(path: str) -> str | None:
    if path.startswith("/auth/"):
        return "auth"
    if path.startswith("/assistant/") or path.startswith("/ai/"):
        return "assistant"
    if path.startswith("/exchanges/"):
        return "exchange"
    return None


def is_rate_limited(request: Request) -> bool:
    """Return whether this request exceeds its endpoint-group/IP allowance."""
    group = sensitive_endpoint_group(request.url.path)
    if group is None:
        return False
    client = request.client.host if request.client else "unknown"
    bucket = _requests[f"{group}:{client}"]
    now = monotonic()
    while bucket and bucket[0] <= now - _WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= _LIMITS[group]:
        return True
    bucket.append(now)
    return False
