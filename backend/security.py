"""Small, dependency-free security controls used by the API."""

from __future__ import annotations

import os
from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class InMemoryRateLimiter:
    """Rate limit a small number of sensitive endpoints per client IP.

    This protects a single API process during development and pilot use. A
    shared limiter (Redis or an API gateway) should replace it before running
    multiple backend workers.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = max(1, limit)
        self.window_seconds = max(1, window_seconds)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = max(1, int(hits[0] + self.window_seconds - now))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again later.",
                    headers={"Retry-After": str(retry_after)},
                )
            hits.append(now)


auth_rate_limiter = InMemoryRateLimiter(
    limit=int(os.getenv("AUTH_RATE_LIMIT_MAX", "10")),
    window_seconds=int(os.getenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "300")),
)


def rate_limit_auth(request: Request) -> None:
    client_host = request.client.host if request.client else "unknown"
    auth_rate_limiter.check(f"{client_host}:{request.url.path}")


def allow_public_host_registration() -> bool:
    default = os.getenv("APP_ENV", "development").lower() != "production"
    return env_bool("ALLOW_PUBLIC_HOST_REGISTRATION", default)
