from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

security_logger = logging.getLogger("tiny_market.security")

_FALLBACK_DOCUMENTS = {
    400: (
        "잘못된 요청",
        "요청을 처리할 수 없습니다. 입력 내용과 주소를 확인해 주세요.",
    ),
    403: (
        "접근할 수 없음",
        "이 요청을 수행할 권한이 없습니다.",
    ),
    404: (
        "페이지를 찾을 수 없음",
        "요청한 페이지를 찾을 수 없습니다.",
    ),
    500: (
        "일시적인 오류",
        "요청을 처리하는 중 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.",
    ),
}


def _standalone_error_response(status: int) -> HttpResponse:
    """Return a dependency-free page when normal template rendering fails."""

    title, message = _FALLBACK_DOCUMENTS[status]
    # The document is static by design: no request/exception data, template
    # engine, context processor, static lookup, or URL reversal is involved.
    document = (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f"<title>{status} {title}</title></head><body><main>"
        f"<h1>{title}</h1><p>{message}</p>"
        "</main></body></html>"
    )
    return HttpResponse(document, status=status, content_type="text/html; charset=utf-8")


def _render_error(request: HttpRequest, status: int) -> HttpResponse:
    try:
        return render(request, f"{status}.html", status=status)
    except Exception:
        # Rendering an error page must never recurse into Django's technical
        # exception view. Keep the log generic for the same reason as the
        # exception middleware.
        security_logger.error("error_template_render_failed status=%d", status)
        return _standalone_error_response(status)


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    security_logger.warning("csrf_rejected")
    return _render_error(request, 403)


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _render_error(request, 400)


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _render_error(request, 403)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return _render_error(request, 404)


def server_error(request: HttpRequest) -> HttpResponse:
    return _render_error(request, 500)
