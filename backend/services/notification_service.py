import logging
import os
from typing import Optional

import aiosmtplib
from email.message import EmailMessage

from backend.services.notification_config import firebase_configured, smtp_configured

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
    if not firebase_configured():
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            _firebase_app = firebase_admin.get_app()
        return _firebase_app
    except Exception as exc:
        logger.warning("Firebase init failed: %s", exc)
        return None


def send_push_notification(fcm_token: str, title: str, body: str) -> bool:
    app = _get_firebase_app()
    if not app:
        logger.info("Firebase not configured; skipping push to %s...", fcm_token[:12])
        return False

    try:
        from firebase_admin import messaging

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=fcm_token,
        )
        messaging.send(message)
        return True
    except Exception as exc:
        logger.warning("Push failed for token %s: %s", fcm_token[:12], exc)
        return False


def send_push_batch(tokens: list[str], title: str, body: str) -> int:
    """Send push notifications to multiple devices using Firebase multicast.

    Returns the number of successfully sent notifications.
    """
    app = _get_firebase_app()
    if not app or not tokens:
        logger.info("Firebase not configured or no tokens; skipping batch push")
        return 0

    try:
        from firebase_admin import messaging

        # Firebase limits multicast to 500 tokens per call
        success_count = 0
        for i in range(0, len(tokens), 500):
            batch = tokens[i : i + 500]
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                tokens=batch,
            )
            response = messaging.send_each_for_multicast(message)
            success_count += response.success_count
            if response.failure_count > 0:
                logger.warning(
                    "Batch push: %d/%d failed in batch starting at index %d",
                    response.failure_count,
                    len(batch),
                    i,
                )
        return success_count
    except Exception as exc:
        logger.warning("Batch push failed: %s", exc)
        return 0


async def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_configured():
        logger.info("SMTP not configured; skipping email to %s", to_email)
        return False

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user,
            password=smtp_password,
            start_tls=True,
        )
        return True
    except Exception as exc:
        logger.warning("Email failed for %s: %s", to_email, exc)
        return False


async def send_email_batch(recipients: list[tuple[str, str, str]]) -> int:
    """Send emails to multiple recipients reusing a single SMTP connection.

    Args:
        recipients: List of (to_email, subject, body) tuples.

    Returns the number of successfully sent emails.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)
    smtp_port = int(os.getenv("SMTP_PORT", "587"))

    if not smtp_configured() or not recipients:
        return 0

    success_count = 0
    try:
        smtp = aiosmtplib.SMTP(hostname=smtp_host, port=smtp_port)
        await smtp.connect()
        await smtp.starttls()
        await smtp.login(smtp_user, smtp_password)

        for to_email, subject, body in recipients:
            msg = EmailMessage()
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.set_content(body)
            try:
                await smtp.send_message(msg)
                success_count += 1
            except Exception as exc:
                logger.warning("Email failed for %s: %s", to_email, exc)

        await smtp.quit()
    except Exception as exc:
        logger.warning("SMTP batch connection failed: %s", exc)

    return success_count


def default_notify_message(event_title: str, location: Optional[str]) -> str:
    loc = location or "the venue"
    return f"Reminder: {event_title} is starting now at {loc}. Please attend."
