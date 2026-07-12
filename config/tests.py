import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .settings import env_bool

SETTINGS_PATH = Path(__file__).with_name("settings.py")
TEST_SECRET_KEY = "test-only-0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%"
VALID_PRODUCTION_ENV = {
    "DJANGO_ENV": "production",
    "DJANGO_DEBUG": "false",
    "DJANGO_ENABLE_ADMIN": "false",
    "DJANGO_SECRET_KEY": TEST_SECRET_KEY,
    "DJANGO_ALLOWED_HOSTS": "market.example.test",
    "DJANGO_SECURE_SSL_REDIRECT": "true",
}


def load_isolated_settings(**overrides: str):
    """Execute settings.py with a clean environment, as a fresh process would."""
    environment = {**VALID_PRODUCTION_ENV, **overrides}
    with patch.dict(os.environ, environment, clear=True):
        spec = importlib.util.spec_from_file_location(
            "config._isolated_settings_for_tests", SETTINGS_PATH
        )
        if spec is None or spec.loader is None:
            raise AssertionError("Unable to load the settings module for testing.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class EnvironmentBooleanTests(SimpleTestCase):
    def test_env_bool_parses_every_allowed_true_value(self):
        for value in ("1", "true", "yes", "on", " TRUE ", "Yes", "ON"):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"TEST_BOOLEAN": value}, clear=True),
            ):
                self.assertIs(env_bool("TEST_BOOLEAN"), True)

    def test_env_bool_parses_every_allowed_false_value(self):
        for value in ("0", "false", "no", "off", " FALSE ", "No", "OFF"):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"TEST_BOOLEAN": value}, clear=True),
            ):
                self.assertIs(env_bool("TEST_BOOLEAN"), False)

    def test_env_bool_uses_default_only_when_variable_is_absent(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIs(env_bool("TEST_BOOLEAN", default=True), True)
            self.assertIs(env_bool("TEST_BOOLEAN", default=False), False)

    def test_env_bool_rejects_empty_or_misspelled_values(self):
        for value in ("", "2", "truthy", "flase", "enabled"):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"TEST_BOOLEAN": value}, clear=True),
            ):
                with self.assertRaisesRegex(
                    ImproperlyConfigured,
                    "TEST_BOOLEAN must be one of",
                ):
                    env_bool("TEST_BOOLEAN")


class ProductionSettingsTests(SimpleTestCase):
    def test_production_rejects_short_secret_key_at_startup(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "at least 50 characters"):
            load_isolated_settings(DJANGO_SECRET_KEY="too-short")

    def test_production_rejects_low_entropy_secret_key_at_startup(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "high-entropy"):
            load_isolated_settings(DJANGO_SECRET_KEY="a" * 50)

    def test_production_rejects_django_insecure_secret_key_at_startup(self):
        insecure_key = "django-insecure-" + TEST_SECRET_KEY

        with self.assertRaisesRegex(ImproperlyConfigured, "high-entropy"):
            load_isolated_settings(DJANGO_SECRET_KEY=insecure_key)

    def test_production_rejects_disabled_ssl_redirect_at_startup(self):
        with self.assertRaisesRegex(
            ImproperlyConfigured,
            "DJANGO_SECURE_SSL_REDIRECT cannot be false",
        ):
            load_isolated_settings(DJANGO_SECURE_SSL_REDIRECT="false")

    def test_valid_production_environment_passes_deployment_checks(self):
        production = load_isolated_settings()
        deployment_settings = {
            name: getattr(production, name)
            for name in (
                "ALLOWED_HOSTS",
                "CSRF_COOKIE_SECURE",
                "DEBUG",
                "SECRET_KEY",
                "SECURE_HSTS_INCLUDE_SUBDOMAINS",
                "SECURE_HSTS_PRELOAD",
                "SECURE_HSTS_SECONDS",
                "SECURE_SSL_REDIRECT",
                "SESSION_COOKIE_SECURE",
            )
        }

        self.assertEqual(production.ENVIRONMENT, "production")
        self.assertFalse(production.DEBUG)
        self.assertTrue(production.SECURE_SSL_REDIRECT)
        with override_settings(**deployment_settings):
            errors = run_checks(include_deployment_checks=True)

        self.assertEqual(errors, [])
