import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.security import validate_production_settings


class ProductionSecurityConfigTests(unittest.TestCase):
    def valid_environment(self):
        return {
            "APP_ENV": "production",
            "JWT_SECRET": "a" * 64,
            "CORS_ORIGINS": "https://app.example.com",
            "TRUSTED_HOSTS": "api.example.com",
            "DATABASE_URL": "postgresql+psycopg://app:password@db.example.com/qrevent",
            "ALLOW_PUBLIC_HOST_REGISTRATION": "false",
        }

    def assert_rejected(self, **overrides):
        environment = self.valid_environment()
        environment.update(overrides)
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(RuntimeError):
                validate_production_settings()

    def test_accepts_explicit_secure_production_settings(self):
        with patch.dict(os.environ, self.valid_environment(), clear=True):
            validate_production_settings()

    def test_rejects_weak_jwt_secret(self):
        self.assert_rejected(JWT_SECRET="short-secret")

    def test_rejects_wildcard_or_missing_cors(self):
        self.assert_rejected(CORS_ORIGINS="*")
        self.assert_rejected(CORS_ORIGINS="")

    def test_rejects_missing_or_wildcard_trusted_hosts(self):
        self.assert_rejected(TRUSTED_HOSTS="")
        self.assert_rejected(TRUSTED_HOSTS="*")

    def test_rejects_sqlite_and_public_host_registration(self):
        self.assert_rejected(DATABASE_URL="sqlite:///./qrevent.db")
        self.assert_rejected(ALLOW_PUBLIC_HOST_REGISTRATION="true")


if __name__ == "__main__":
    unittest.main()
