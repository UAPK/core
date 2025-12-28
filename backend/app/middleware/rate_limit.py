"""Rate limiting for FastAPI using slowapi.

Keying strategy:
- If X-API-Key present: rate limit per API key (hashed)
- Else: per client IP
"""

from __future__ import annotations

import hashlib
from typing import Optional

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address


def _key_func(request) -> str:
    api_key = request.headers.get("X-API-Key")
    if api_key:
        digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        return f"api_key:{digest}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_key_func)


def setup_rate_limiting(app, default_limits: Optional[list[str]] = None) -> None:
    # Apply a default limit to all routes via middleware.
    # You can still override per-route with @limiter.limit(...)
    if default_limits:
        limiter.default_limits = default_limits
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
