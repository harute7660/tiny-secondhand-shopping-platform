from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpRequest, HttpResponse

from .views import (
    bad_request,
    page_not_found,
    permission_denied,
    security_logger,
    server_error,
)


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
