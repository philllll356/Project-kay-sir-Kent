import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.notification_config import (  # noqa: E402
    firebase_configured,
    notification_status,
    smtp_configured,
)


class NotificationConfigTests(unittest.TestCase):
    def test_missing_providers_are_disabled(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(firebase_configured())
            self.assertFalse(smtp_configured())
            self.assertEqual(
                notification_status(),
                {"firebase_configured": False, "smtp_configured": False},
            )

    def test_placeholder_smtp_values_are_disabled(self):
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.gmail.com",
                "SMTP_USER": "your-email@gmail.com",
                "SMTP_PASSWORD": "your-app-password",
                "SMTP_FROM": "your-email@gmail.com",
            },
            clear=True,
        ):
            self.assertFalse(smtp_configured())

    def test_complete_smtp_configuration_is_detected_without_sending(self):
        with patch.dict(
            os.environ,
            {
                "SMTP_HOST": "smtp.example.com",
                "SMTP_USER": "mailer@example.com",
                "SMTP_PASSWORD": "a-real-test-secret",
                "SMTP_FROM": "mailer@example.com",
                "SMTP_PORT": "587",
            },
            clear=True,
        ):
            self.assertTrue(smtp_configured())

    def test_existing_firebase_credentials_file_is_detected(self):
        with tempfile.NamedTemporaryFile(suffix=".json") as credentials_file:
            with patch.dict(
                os.environ,
                {"FIREBASE_CREDENTIALS_PATH": credentials_file.name},
                clear=True,
            ):
                self.assertTrue(firebase_configured())


if __name__ == "__main__":
    unittest.main()
