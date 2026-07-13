import importlib.util
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.checks import run_checks
from django.core.exceptions import ImproperlyConfigured, PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path

from .settings import env_bool
from .urls import urlpatterns as application_urlpatterns

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

SAFE_EXCEPTION_MIDDLEWARE = "config.middleware.SafeExceptionMiddleware"
TEST_MIDDLEWARE = [
    *(item for item in settings.MIDDLEWARE if item != SAFE_EXCEPTION_MIDDLEWARE),
    SAFE_EXCEPTION_MIDDLEWARE,
]
SENSITIVE_EXCEPTION_MARKER = "assessment-password=NeverExposeThis-2026!"
SENSITIVE_PATH_MARKER = "C:\\Users\\student\\private-project\\settings.py"


def exception_view(request):
    raise RuntimeError(f"{SENSITIVE_EXCEPTION_MARKER} at {SENSITIVE_PATH_MARKER}")


def suspicious_view(request):
    raise SuspiciousOperation(f"bad input {SENSITIVE_EXCEPTION_MARKER}")


def forbidden_view(request):
    raise PermissionDenied(f"private rule {SENSITIVE_EXCEPTION_MARKER}")


def missing_view(request):
    raise Http404(f"private object {SENSITIVE_EXCEPTION_MARKER}")


def csrf_probe_view(request):
    return HttpResponse("accepted")


def ordinary_bad_response_view(request):
    return JsonResponse({"field": ["사용자에게 보여 줄 검증 오류"]}, status=400)


def ordinary_missing_response_view(request):
    return JsonResponse({"detail": "공개할 수 없는 항목입니다."}, status=404)


def method_not_allowed_view(request):
    return HttpResponseNotAllowed(["GET"])


def throttled_view(request):
    return JsonResponse({"detail": "잠시 후 다시 시도해 주세요."}, status=429)


# A private URLConf lets the security boundary be tested without adding
# deliberate exception routes to the application itself.
urlpatterns = [
    path("__test__/exception/", exception_view),
    path("__test__/suspicious/", suspicious_view),
    path("__test__/forbidden/", forbidden_view),
    path("__test__/missing/", missing_view),
    path("__test__/csrf/", csrf_probe_view),
    path("__test__/ordinary-400/", ordinary_bad_response_view),
    path("__test__/ordinary-404/", ordinary_missing_response_view),
    path("__test__/method/", method_not_allowed_view),
    path("__test__/throttled/", throttled_view),
    *application_urlpatterns,
]

handler400 = "config.views.bad_request"
handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"


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


class ErrorResponseAssertions:
    def assert_security_headers(self, response):
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["Pragma"], "no-cache")

    def assert_no_diagnostics(self, response, *extra_markers):
        body = response.content.decode("utf-8").lower()
        forbidden_markers = (
            SENSITIVE_EXCEPTION_MARKER,
            SENSITIVE_PATH_MARKER,
            "traceback",
            "runtimeerror",
            "exception type",
            "exception value",
            "django version",
            "python version",
            "python executable",
            "installed applications",
            "secret_key",
            *extra_markers,
        )
        for marker in forbidden_markers:
            with self.subTest(marker=marker):
                self.assertNotIn(marker.lower(), body)


@override_settings(
    DEBUG=True,
    MIDDLEWARE=TEST_MIDDLEWARE,
    ROOT_URLCONF=__name__,
    SECURE_SSL_REDIRECT=False,
)
class DebugSafeExceptionTests(ErrorResponseAssertions, SimpleTestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_unhandled_post_exception_never_returns_technical_debug_page(self):
        submitted_password = "Posted-Password-Must-Not-Appear!"

        with self.assertLogs("tiny_market.security", level="ERROR") as captured:
            response = self.client.post(
                "/__test__/exception/",
                {
                    "password": submitted_password,
                    "confirmation": submitted_password,
                },
            )

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "TEMPORARY ERROR", status_code=500)
        self.assert_no_diagnostics(response, submitted_password)
        self.assert_security_headers(response)

        log_output = " ".join(captured.output)
        self.assertIn("unhandled_request_exception", log_output)
        for marker in (
            submitted_password,
            SENSITIVE_EXCEPTION_MARKER,
            SENSITIVE_PATH_MARKER,
            "RuntimeError",
        ):
            self.assertNotIn(marker, log_output)

    def test_render_failure_uses_static_fallback_with_security_headers(self):
        render_failure_marker = "template-secret / private/base.html"

        with (
            patch(
                "config.views.render",
                side_effect=RuntimeError(render_failure_marker),
            ),
            self.assertLogs("tiny_market.security", level="ERROR") as captured,
        ):
            response = self.client.get("/__test__/exception/")

        self.assertEqual(response.status_code, 500)
        self.assertContains(response, "일시적인 오류", status_code=500)
        self.assert_no_diagnostics(response, render_failure_marker)
        self.assert_security_headers(response)
        self.assertIn("error_template_render_failed status=500", " ".join(captured.output))
        self.assertNotIn(render_failure_marker, " ".join(captured.output))

    def test_expected_http_exceptions_keep_their_status_in_debug_mode(self):
        for request_path, status in (
            ("/__test__/suspicious/", 400),
            ("/__test__/forbidden/", 403),
            ("/__test__/missing/", 404),
        ):
            with self.subTest(path=request_path):
                response = self.client.get(request_path)
                self.assertEqual(response.status_code, status)
                self.assert_no_diagnostics(response)
                self.assert_security_headers(response)

    def test_unmatched_url_does_not_disclose_url_patterns_in_debug_mode(self):
        response = self.client.get("/__test__/not-in-urlconf/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "PAGE NOT FOUND", status_code=404)
        self.assert_no_diagnostics(
            response,
            "using the urlconf defined in",
            "url patterns",
            "config.tests",
        )
        self.assert_security_headers(response)

    def test_resolved_view_json_404_is_not_rewritten_in_debug_mode(self):
        response = self.client.get("/__test__/ordinary-404/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"detail": "공개할 수 없는 항목입니다."})
        self.assert_security_headers(response)


@override_settings(
    DEBUG=False,
    MIDDLEWARE=TEST_MIDDLEWARE,
    ROOT_URLCONF=__name__,
    SECURE_SSL_REDIRECT=False,
)
class ProductionErrorResponseTests(ErrorResponseAssertions, SimpleTestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)

    def test_custom_400_403_404_and_500_responses_are_non_diagnostic(self):
        for request_path, status in (
            ("/__test__/suspicious/", 400),
            ("/__test__/forbidden/", 403),
            ("/__test__/missing/", 404),
            ("/__test__/exception/", 500),
            ("/__test__/not-in-urlconf/", 404),
        ):
            with self.subTest(path=request_path):
                response = self.client.get(request_path)
                self.assertEqual(response.status_code, status)
                self.assert_no_diagnostics(response)
                self.assert_security_headers(response)

    def test_csrf_failure_is_custom_non_diagnostic_and_not_cached(self):
        csrf_client = Client(enforce_csrf_checks=True, raise_request_exception=False)
        submitted_password = "Csrf-Rejected-Password-Secret!"

        with self.assertLogs("tiny_market.security", level="WARNING") as captured:
            response = csrf_client.post(
                "/__test__/csrf/",
                {"password": submitted_password},
            )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "ACCESS DENIED", status_code=403)
        self.assert_no_diagnostics(response, submitted_password)
        self.assert_security_headers(response)
        self.assertIn("csrf_rejected", " ".join(captured.output))
        self.assertNotIn(submitted_password, " ".join(captured.output))

    def test_normal_400_405_and_429_responses_are_not_rewritten(self):
        bad_response = self.client.get("/__test__/ordinary-400/")
        method_response = self.client.post("/__test__/method/")
        throttled_response = self.client.get("/__test__/throttled/")

        self.assertEqual(
            bad_response.json(),
            {"field": ["사용자에게 보여 줄 검증 오류"]},
        )
        self.assertEqual(method_response.status_code, 405)
        self.assertEqual(method_response.headers["Allow"], "GET")
        self.assertEqual(
            throttled_response.json(),
            {"detail": "잠시 후 다시 시도해 주세요."},
        )
        for response in (bad_response, method_response, throttled_response):
            self.assert_security_headers(response)
