from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import PermissionDenied, RequestDataTooBig, SuspiciousOperation
from django.core.files.uploadhandler import FileUploadHandler
from django.http import Http404, HttpRequest, HttpResponse

from .views import (
    bad_request,
    page_not_found,
    permission_denied,
    security_logger,
    server_error,
)

_UPLOAD_LIMIT_EXCEEDED_ATTRIBUTE = "_multipart_upload_limit_exceeded"


class CumulativeUploadLimitHandler(FileUploadHandler):
    """Pass file chunks through while enforcing one limit across all files."""

    def __init__(self, request: HttpRequest, *, max_bytes: int) -> None:
        super().__init__(request)
        self.max_bytes = max_bytes
        self.received_bytes = 0

    def receive_data_chunk(self, raw_data: bytes, start: int) -> bytes:
        # ``start`` is reset for every file, so keep a request-wide counter of
        # our own. This also covers a missing, chunked, or understated request
        # Content-Length whenever the server streams multipart data to Django.
        self.received_bytes += len(raw_data)
        if self.received_bytes > self.max_bytes:
            setattr(self.request, _UPLOAD_LIMIT_EXCEEDED_ATTRIBUTE, True)
            raise RequestDataTooBig("Multipart upload exceeded the configured limit.")
        return raw_data

    def file_complete(self, file_size: int) -> None:
        # A later handler still creates the UploadedFile. Returning None keeps
        # this handler transparent apart from its cumulative byte accounting.
        return None


class MultipartUploadLimitMiddleware:
    """Reject oversized multipart writes before CSRF or view parsing begins."""

    limited_methods = frozenset({"POST", "PUT", "PATCH"})

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not self._is_limited_multipart_request(request):
            return self.get_response(request)

        max_bytes = settings.MULTIPART_UPLOAD_MAX_BYTES
        content_length = self._content_length(request)
        if content_length is not None and content_length > max_bytes:
            return self._limit_response(request)

        # Install before CsrfViewMiddleware: CSRF may access request.POST and
        # therefore start multipart parsing before the selected view runs.
        request.upload_handlers.insert(
            0,
            CumulativeUploadLimitHandler(request, max_bytes=max_bytes),
        )

        try:
            response = self.get_response(request)
        except RequestDataTooBig:
            # Only consume the exception raised by our handler. Existing
            # DATA_UPLOAD_MAX_MEMORY_SIZE failures keep Django's normal flow.
            if not getattr(request, _UPLOAD_LIMIT_EXCEEDED_ATTRIBUTE, False):
                raise
            return self._limit_response(request)

        # Django may already have converted a SuspiciousOperation raised while
        # parsing into a response. Replace it so DEBUG can never expose a
        # technical exception page or the handler's internal message.
        if getattr(request, _UPLOAD_LIMIT_EXCEEDED_ATTRIBUTE, False):
            return self._limit_response(request)
        return response

    @classmethod
    def _is_limited_multipart_request(cls, request: HttpRequest) -> bool:
        if request.method not in cls.limited_methods:
            return False
        media_type = request.META.get("CONTENT_TYPE", "").partition(";")[0]
        return media_type.strip().lower().startswith("multipart/")

    @staticmethod
    def _content_length(request: HttpRequest) -> int | None:
        value = request.META.get("CONTENT_LENGTH")
        if value in (None, ""):
            return None
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    @staticmethod
    def _limit_response(request: HttpRequest) -> HttpResponse:
        setattr(request, _UPLOAD_LIMIT_EXCEEDED_ATTRIBUTE, True)
        return bad_request(request, RequestDataTooBig())


class TrustedProxyHeadersMiddleware:
    """Discard HTTPS forwarding headers unless the direct peer is trusted."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.META.get("REMOTE_ADDR", "") not in settings.TRUSTED_PROXY_IPS:
            request.META.pop("HTTP_X_FORWARDED_PROTO", None)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Add an application-specific CSP and prevent private-page caching."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)

        if request.path.startswith("/admin/"):
            # Django admin currently needs small inline style/script snippets.
            # The public product surface remains strict below.
            csp = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "object-src 'none'; base-uri 'self'; frame-ancestors 'none'; "
                "form-action 'self'"
            )
        else:
            csp = (
                "default-src 'self'; "
                "img-src 'self' data:; "
                "style-src 'self'; script-src 'self'; connect-src 'self'; "
                "font-src 'self'; object-src 'none'; base-uri 'self'; "
                "frame-ancestors 'none'; form-action 'self'"
            )

        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")

        # Product and moderation state can change at any time. Do not let a
        # browser or shared proxy resurrect titles, descriptions, prices, or
        # evidence after a listing is blocked/deleted. Static assets are served
        # separately in production and may use their own immutable cache policy.
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["Pragma"] = "no-cache"

        return response


class SafeExceptionMiddleware:
    """Turn view/template exceptions into non-diagnostic browser responses.

    Django intentionally shows detailed exception pages while ``DEBUG`` is
    enabled. That is useful on a developer-only machine, but unsafe for this
    demonstrator because the browser may be shared during assessment. This
    exception hook runs in both modes and never interpolates exception data,
    request bodies, or filesystem paths into the response or security log.

    Ordinary responses with a 4xx status are not touched. In particular, a
    form or JSON view remains responsible for its own validation response.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        if (
            settings.DEBUG
            and response.status_code == 404
            and getattr(request, "resolver_match", None) is None
        ):
            # Resolver404 is raised before Django enters its view-exception
            # hook. In DEBUG mode Django otherwise renders every URL pattern
            # in the project. A resolved view's deliberate HTML/JSON 404 has a
            # resolver_match and is therefore preserved unchanged.
            return page_not_found(request, Http404())
        return response

    def process_exception(
        self,
        request: HttpRequest,
        exception: Exception,
    ) -> HttpResponse:
        if isinstance(exception, Http404):
            return page_not_found(request, exception)
        if isinstance(exception, PermissionDenied):
            return permission_denied(request, exception)
        if isinstance(exception, SuspiciousOperation):
            return bad_request(request, exception)

        # Do not pass ``exception`` or request-controlled values to the logger.
        # The event is still available for operational alerting without
        # exposing passwords, tokens, local paths, or exception messages.
        security_logger.error("unhandled_request_exception")
        return server_error(request)
