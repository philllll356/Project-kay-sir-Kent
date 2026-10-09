"""Provider configuration checks that never expose notification secrets."""

from __future__ import annotations

import os


def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.strip().lower()
    return normalized in {
        "your-email@gmail.com",
        "your-app-password",
        "firebase-service-account.json",
        "change-me",
    } or normalized.startswith("your-")


def firebase_configured() -> bool:
    credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
    return bool(credentials_path) and not _is_placeholder(credentials_path) and os.path.isfile(credentials_path)


def smtp_configured() -> bool:
    values = (
        os.getenv("SMTP_HOST"),
        os.getenv("SMTP_USER"),
        os.getenv("SMTP_PASSWORD"),
        os.getenv("SMTP_FROM"),
    )
    if any(_is_placeholder(value) for value in values):
        return False
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        return False
    return 1 <= port <= 65535


def notification_status() -> dict[str, bool]:
    return {
        "firebase_configured": firebase_configured(),
        "smtp_configured": smtp_configured(),
    }
