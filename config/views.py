from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

security_logger = logging.getLogger("tiny_market.security")


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    security_logger.warning("csrf_rejected path=%s", request.path)
    return render(request, "403.html", status=403)


def bad_request(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "400.html", status=400)


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "403.html", status=403)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "404.html", status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)
