"""Server-side verification for Google OpenID Connect ID tokens."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from google.auth import exceptions as google_exceptions


@dataclass(frozen=True)
class GoogleIdentity:
    subject: str
    email: str
    name: str


def _client_ids() -> list[str]:
    return [
        value.strip()
        for value in os.getenv("GOOGLE_CLIENT_IDS", "").split(",")
        if value.strip()
    ]


def verify_google_id_token(raw_token: str) -> GoogleIdentity:
    client_ids = _client_ids()
    if not client_ids:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured yet.",
        )

    claims = None
    request = google_requests.Request()
    for client_id in client_ids:
        try:
            claims = id_token.verify_oauth2_token(raw_token, request, audience=client_id)
            break
        except (ValueError, google_exceptions.GoogleAuthError):
            continue

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google sign-in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = str(claims.get("email", "")).lower().strip()
    subject = str(claims.get("sub", "")).strip()
    email_verified = claims.get("email_verified") is True
    allowed_domain = os.getenv("GOOGLE_ALLOWED_DOMAIN", "").lower().strip()
    hosted_domain = str(claims.get("hd", "")).lower().strip()

    if not subject or not email or not email_verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account email is not verified.")
    if allowed_domain and hosted_domain != allowed_domain:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This Google account is outside the school domain.")

    return GoogleIdentity(
        subject=subject,
        email=email,
        name=str(claims.get("name", email)).strip()[:255],
    )
