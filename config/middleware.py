from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse


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
