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
    # Instructor accounts should be provisioned by an administrator. Public
    # registration must be explicitly enabled for a temporary local demo.
    return env_bool("ALLOW_PUBLIC_HOST_REGISTRATION", False)


def _csv_environment_value(name: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, "").split(",") if value.strip()]


def validate_production_settings() -> None:
    """Reject unsafe deployment settings before a production API starts."""
    if os.getenv("APP_ENV", "development").strip().lower() != "production":
        return

    jwt_secret = os.getenv("JWT_SECRET", "")
    if jwt_secret == "dev-secret-change-in-production" or len(jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be a long random value in production")

    cors_origins = _csv_environment_value("CORS_ORIGINS")
    if not cors_origins or "*" in cors_origins:
        raise RuntimeError("CORS_ORIGINS must explicitly list trusted production origins")

    trusted_hosts = _csv_environment_value("TRUSTED_HOSTS")
    if not trusted_hosts or "*" in trusted_hosts:
        raise RuntimeError("TRUSTED_HOSTS must explicitly list trusted production hosts")

    database_url = os.getenv("DATABASE_URL", "").strip().lower()
    if not database_url or database_url.startswith("sqlite"):
        raise RuntimeError("DATABASE_URL must use PostgreSQL in production")

    if allow_public_host_registration():
        raise RuntimeError("Public host registration must be disabled in production")
