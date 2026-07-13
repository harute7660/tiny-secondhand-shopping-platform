import importlib.util
import json
import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.checks import run_checks
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    RequestDataTooBig,
    SuspiciousOperation,
)
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.handlers.asgi import ASGIRequest
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import path

from .middleware import (
    CumulativeUploadLimitHandler,
    MultipartAdmissionMiddleware,
    MultipartUploadLimitMiddleware,
)
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


def multipart_probe_view(request):
    files = request.FILES.getlist("files")
    return JsonResponse(
        {
            "file_count": len(files),
            "file_bytes": sum(upload.size for upload in files),
        }
    )


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
    path("__test__/multipart/", multipart_probe_view),
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
class MultipartUploadLimitTests(ErrorResponseAssertions, SimpleTestCase):
    def setUp(self):
        self.client = Client(raise_request_exception=False)
        self.factory = RequestFactory()

    def test_upload_boundaries_are_ordered_before_csrf_and_keep_existing_policies(self):
        middleware = settings.MIDDLEWARE

        self.assertLess(
            middleware.index("config.middleware.MultipartUploadLimitMiddleware"),
            middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"),
        )
        self.assertLess(
            middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"),
            middleware.index("config.middleware.MultipartAdmissionMiddleware"),
        )
        self.assertLess(
            middleware.index("config.middleware.MultipartAdmissionMiddleware"),
            middleware.index("django.middleware.csrf.CsrfViewMiddleware"),
        )
        self.assertEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 6 * 1024 * 1024)
        self.assertEqual(settings.FILE_UPLOAD_MAX_MEMORY_SIZE, 5 * 1024 * 1024)
        self.assertEqual(settings.DATA_UPLOAD_MAX_NUMBER_FILES, 5)
        self.assertEqual(settings.MULTIPART_UPLOAD_MAX_BYTES, 21 * 1024 * 1024)
        self.assertGreater(settings.MULTIPART_UPLOAD_MAX_BYTES, 20 * 1024 * 1024)

    def test_known_oversized_length_rejects_all_write_methods_before_downstream(self):
        for method in ("POST", "PUT", "PATCH"):
            with self.subTest(method=method):
                request = self.factory.generic(
                    method,
                    "/__test__/multipart/",
                    data=b"--upload-boundary--\r\n",
                    content_type="multipart/form-data; boundary=upload-boundary",
                )
                request.META["CONTENT_LENGTH"] = str(settings.MULTIPART_UPLOAD_MAX_BYTES + 1)
                downstream_calls = []

                def downstream(inner_request, calls=downstream_calls):
                    calls.append(inner_request)
                    return HttpResponse("must not run")

                response = MultipartUploadLimitMiddleware(downstream)(request)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(downstream_calls, [])
                self.assertFalse(request._read_started)
                self.assertFalse(hasattr(request, "_files"))
                self.assert_no_diagnostics(
                    response,
                    "multipart upload exceeded",
                    "requestdatatoobig",
                )

    def test_cumulative_handler_does_not_reset_between_files(self):
        request = self.factory.post("/__test__/multipart/")
        handler = CumulativeUploadLimitHandler(request, max_bytes=5)

        handler.new_file("files", "one.bin", "application/octet-stream", 3)
        self.assertEqual(handler.receive_data_chunk(b"abc", 0), b"abc")
        self.assertIsNone(handler.file_complete(3))
        handler.new_file("files", "two.bin", "application/octet-stream", 3)

        with self.assertRaises(RequestDataTooBig):
            handler.receive_data_chunk(b"def", 0)

        self.assertEqual(handler.received_bytes, 6)

    @override_settings(MULTIPART_UPLOAD_MAX_BYTES=5)
    def test_understated_length_is_caught_while_parser_streams_all_file_chunks(self):
        body = encode_multipart(
            BOUNDARY,
            {
                "files": [
                    SimpleUploadedFile("one.bin", b"abc"),
                    SimpleUploadedFile("two.bin", b"def"),
                ]
            },
        )
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/__test__/multipart/",
            "query_string": b"",
            "headers": [
                (b"content-type", MULTIPART_CONTENT.encode("ascii")),
                # ASGI supplies the complete de-chunked stream. Deliberately
                # understate the untrusted header so only chunk accounting can
                # catch the combined six bytes.
                (b"content-length", b"1"),
            ],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
        }
        request = ASGIRequest(scope, BytesIO(body))

        def parse_files(inner_request):
            inner_request.FILES.getlist("files")
            return HttpResponse("must not succeed")

        response = MultipartUploadLimitMiddleware(parse_files)(request)

        self.assertEqual(response.status_code, 400)
        self.assert_no_diagnostics(
            response,
            "multipart upload exceeded",
            "requestdatatoobig",
        )

    @override_settings(MULTIPART_UPLOAD_MAX_BYTES=5)
    def test_missing_chunked_length_installs_the_same_cumulative_guard(self):
        request = self.factory.generic(
            "POST",
            "/__test__/multipart/",
            content_type="multipart/form-data; boundary=upload-boundary",
        )
        request.META["CONTENT_TYPE"] = "multipart/form-data; boundary=upload-boundary"
        request.META.pop("CONTENT_LENGTH", None)
        request.META["HTTP_TRANSFER_ENCODING"] = "chunked"

        def stream_chunks(inner_request):
            handler = inner_request.upload_handlers[0]
            handler.receive_data_chunk(b"abc", 0)
            handler.file_complete(3)
            handler.receive_data_chunk(b"def", 0)
            return HttpResponse("must not succeed")

        response = MultipartUploadLimitMiddleware(stream_chunks)(request)

        self.assertEqual(response.status_code, 400)
        self.assert_no_diagnostics(
            response,
            "multipart upload exceeded",
            "requestdatatoobig",
        )

    def test_full_stack_oversized_header_returns_safe_400_with_security_headers(self):
        response = self.client.generic(
            "POST",
            "/__test__/multipart/",
            data=b"--upload-boundary--\r\n",
            content_type="multipart/form-data; boundary=upload-boundary",
            CONTENT_LENGTH=str(settings.MULTIPART_UPLOAD_MAX_BYTES + 1),
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "BAD REQUEST", status_code=400)
        self.assert_no_diagnostics(
            response,
            "multipart upload exceeded",
            "requestdatatoobig",
        )
        self.assert_security_headers(response)

    def test_full_stack_non_listing_multipart_still_reaches_file_parsing(self):
        response = self.client.post(
            "/__test__/multipart/",
            {
                "files": [
                    SimpleUploadedFile("one.txt", b"abc", content_type="text/plain"),
                    SimpleUploadedFile("two.txt", b"defg", content_type="text/plain"),
                ]
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"file_count": 2, "file_bytes": 7})
        self.assert_security_headers(response)

    def test_full_stack_anonymous_listing_multipart_is_rejected_safely(self):
        response = self.client.generic(
            "POST",
            "/listings/new/",
            data=b"--upload-boundary--\r\n",
            content_type="multipart/form-data; boundary=upload-boundary",
        )

        self.assertEqual(response.status_code, 403)
        self.assert_no_diagnostics(response, "upload-boundary")
        self.assert_security_headers(response)


@override_settings(
    DEBUG=True,
    ROOT_URLCONF=__name__,
    SECURE_SSL_REDIRECT=False,
)
class MultipartAdmissionTests(ErrorResponseAssertions, SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.user = SimpleNamespace(is_authenticated=True, pk=731)

    def tearDown(self):
        cache.clear()

    def _multipart_request(self, method="POST", path="/listings/new/"):
        request = self.factory.generic(
            method,
            path,
            data=b"--upload-boundary--\r\n",
            content_type="multipart/form-data; boundary=upload-boundary",
        )
        return request

    def test_anonymous_multipart_writes_never_reach_or_parse_downstream(self):
        for method in ("POST", "PUT", "PATCH"):
            with self.subTest(method=method):
                request = self._multipart_request(method=method)
                request.user = AnonymousUser()
                downstream_calls = []

                def downstream(inner_request, calls=downstream_calls):
                    calls.append(inner_request)
                    inner_request.FILES.getlist("files")
                    return HttpResponse("must not run")

                response = MultipartAdmissionMiddleware(downstream)(request)

                self.assertEqual(response.status_code, 403)
                self.assertEqual(downstream_calls, [])
                self.assertFalse(request._read_started)
                self.assertFalse(hasattr(request, "_post"))
                self.assertFalse(hasattr(request, "_files"))
                self.assertFalse(hasattr(request, "_body"))
                self.assert_no_diagnostics(response, "upload-boundary")

    @override_settings(
        LISTING_MULTIPART_ADMISSION_LIMIT=1,
        LISTING_MULTIPART_ADMISSION_WINDOW_SECONDS=3600,
    )
    def test_listing_create_and_update_excess_is_rejected_before_body_parsing(self):
        paths = (
            "/listings/new/",
            "/listings/11111111-1111-1111-1111-111111111111/edit/",
        )
        for request_path in paths:
            with self.subTest(path=request_path):
                cache.clear()
                downstream_calls = []

                def downstream(inner_request, calls=downstream_calls):
                    calls.append(inner_request)
                    return HttpResponse(status=204)

                middleware = MultipartAdmissionMiddleware(downstream)
                admitted_request = self._multipart_request(path=request_path)
                admitted_request.user = self.user
                admitted_response = middleware(admitted_request)
                rejected_request = self._multipart_request(path=request_path)
                rejected_request.user = self.user
                rejected_response = middleware(rejected_request)

                self.assertEqual(admitted_response.status_code, 204)
                self.assertEqual(rejected_response.status_code, 429)
                self.assertEqual(downstream_calls, [admitted_request])
                self.assertFalse(rejected_request._read_started)
                self.assertFalse(hasattr(rejected_request, "_post"))
                self.assertFalse(hasattr(rejected_request, "_files"))
                self.assertFalse(hasattr(rejected_request, "_body"))
                self.assert_no_diagnostics(rejected_response, "upload-boundary")

    @override_settings(
        LISTING_MULTIPART_ADMISSION_LIMIT=1,
        LISTING_MULTIPART_ADMISSION_WINDOW_SECONDS=3600,
    )
    def test_expired_cache_key_race_retries_with_atomic_add(self):
        request = self._multipart_request(path="/listings/new/")
        request.user = self.user

        with patch("config.middleware.cache") as mocked_cache:
            mocked_cache.add.side_effect = (False, True)
            mocked_cache.incr.side_effect = ValueError
            response = MultipartAdmissionMiddleware(lambda _request: HttpResponse(status=204))(
                request
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(mocked_cache.add.call_count, 2)
        mocked_cache.incr.assert_called_once()

    @override_settings(
        LISTING_MULTIPART_ADMISSION_LIMIT=1,
        LISTING_MULTIPART_ADMISSION_WINDOW_SECONDS=3600,
    )
    def test_foreign_browser_context_is_rejected_without_spending_quota(self):
        for headers in (
            {"HTTP_ORIGIN": "https://untrusted.example"},
            {"HTTP_ORIGIN": "http://["},
            {"HTTP_SEC_FETCH_SITE": "same-site"},
            {"HTTP_SEC_FETCH_SITE": "cross-site"},
        ):
            with self.subTest(headers=headers):
                cache.clear()
                rejected = self._multipart_request(path="/listings/new/")
                rejected.user = self.user
                for name, value in headers.items():
                    rejected.META[name] = value
                downstream_calls = []

                def downstream(inner_request, calls=downstream_calls):
                    calls.append(inner_request)
                    return HttpResponse(status=204)

                middleware = MultipartAdmissionMiddleware(downstream)
                response = middleware(rejected)

                self.assertEqual(response.status_code, 403)
                self.assertEqual(downstream_calls, [])
                self.assertFalse(rejected._read_started)
                self.assertFalse(hasattr(rejected, "_post"))
                self.assertFalse(hasattr(rejected, "_files"))
                self.assertFalse(hasattr(rejected, "_body"))

                same_origin_request = self._multipart_request(path="/listings/new/")
                same_origin_request.user = self.user
                same_origin_request.META["HTTP_ORIGIN"] = "http://testserver"
                same_origin_request.META["HTTP_SEC_FETCH_SITE"] = "same-origin"
                admitted = middleware(same_origin_request)

                self.assertEqual(admitted.status_code, 204)
                self.assertEqual(downstream_calls, [same_origin_request])

    def test_authenticated_non_listing_multipart_still_parses_normally(self):
        request = self.factory.post(
            "/__test__/multipart/",
            {
                "files": [
                    SimpleUploadedFile("one.txt", b"abc", content_type="text/plain"),
                    SimpleUploadedFile("two.txt", b"defg", content_type="text/plain"),
                ]
            },
        )
        request.user = self.user

        response = MultipartAdmissionMiddleware(multipart_probe_view)(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"file_count": 2, "file_bytes": 7})

    def test_anonymous_urlencoded_form_still_reaches_normal_processing(self):
        request = self.factory.generic(
            "POST",
            "/accounts/login/",
            data=urlencode({"username": "alice", "password": "normal-form-value"}),
            content_type="application/x-www-form-urlencoded",
        )
        request.user = AnonymousUser()

        def parse_normal_form(inner_request):
            return JsonResponse({"username": inner_request.POST.get("username")})

        response = MultipartAdmissionMiddleware(parse_normal_form)(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {"username": "alice"})


@override_settings(
    ROOT_URLCONF="config.urls",
    LISTING_MULTIPART_ADMISSION_LIMIT=1,
    LISTING_MULTIPART_ADMISSION_WINDOW_SECONDS=3600,
)
class MultipartAdmissionFullStackTests(ErrorResponseAssertions, TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="multipart-full-stack-user",
            password="Correct-Horse-Battery-99!",  # nosec B106
        )
        self.client.force_login(self.user)
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_listing_admission_429_keeps_outer_security_headers(self):
        data = {
            "title": "입장 제한 보안 헤더 검증 상품",
            "description": "첫 요청만 정상 처리되고 다음 multipart는 파싱 전에 거부됩니다.",
            "price_points": 1000,
            "category": "OTHER",
            "condition": "GOOD",
            "region": "서울",
            "defect_disclosure": "NONE_KNOWN",
        }

        admitted = self.client.post("/listings/new/", data)
        rejected = self.client.post("/listings/new/", data)

        self.assertEqual(admitted.status_code, 302)
        self.assertEqual(rejected.status_code, 429)
        self.assert_security_headers(rejected)
        self.assert_no_diagnostics(rejected, data["title"], data["description"])


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
            response = self.client.generic(
                "POST",
                "/__test__/exception/",
                data=urlencode(
                    {
                        "password": submitted_password,
                        "confirmation": submitted_password,
                    }
                ),
                content_type="application/x-www-form-urlencoded",
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
            response = csrf_client.generic(
                "POST",
                "/__test__/csrf/",
                data=urlencode({"password": submitted_password}),
                content_type="application/x-www-form-urlencoded",
            )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "ACCESS DENIED", status_code=403)
        self.assert_no_diagnostics(response, submitted_password)
        self.assert_security_headers(response)
        self.assertIn("csrf_rejected", " ".join(captured.output))
        self.assertNotIn(submitted_password, " ".join(captured.output))

    def test_normal_400_405_and_429_responses_are_not_rewritten(self):
        bad_response = self.client.get("/__test__/ordinary-400/")
        method_response = self.client.generic(
            "POST",
            "/__test__/method/",
            data="",
            content_type="application/x-www-form-urlencoded",
        )
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
