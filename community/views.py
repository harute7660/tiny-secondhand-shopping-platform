from __future__ import annotations

import logging

from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.cache import cache
from django.db.models import Exists, OuterRef, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_GET, require_POST

from accounts.models import UserBlock

from .forms import GlobalChatMessageForm
from .models import GlobalChatMessage

security_logger = logging.getLogger("tiny_market.security")

INITIAL_MESSAGE_LIMIT = 50
MAX_MESSAGE_LIMIT = 100
SEND_RATE_LIMIT = 10
SEND_RATE_WINDOW = 60
POLL_RATE_LIMIT = 40
POLL_RATE_WINDOW = 60
CURSOR_SALT = "community.global-chat.cursor.v1"
MAX_CURSOR_LENGTH = 256
MAX_DATABASE_ID = 2**63 - 1


def _private_response(response: HttpResponse) -> HttpResponse:
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Pragma"] = "no-cache"
    return response


def _consume_user_limit(user_id: int, action: str, limit: int, window: int) -> bool:
    """Atomically count an authenticated actor in the configured cache."""
    key = f"community:global-chat:{action}:user:{user_id}"
    if cache.add(key, 1, timeout=window):
        return True
    try:
        return cache.incr(key) <= limit
    except ValueError:
        return cache.add(key, 1, timeout=window)


def _rate_limited_json(window: int) -> JsonResponse:
    response = JsonResponse(
        {"error": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."},
        status=429,
    )
    response.headers["Retry-After"] = str(window)
    return _private_response(response)


def _invalid_json() -> JsonResponse:
    return _private_response(JsonResponse({"error": "요청값을 확인해 주세요."}, status=400))


def _encode_cursor(message_id: int) -> str:
    return signing.dumps({"id": message_id}, salt=CURSOR_SALT, compress=True)


def _decode_cursor(value: str) -> int:
    if not value or len(value) > MAX_CURSOR_LENGTH:
        raise signing.BadSignature("invalid cursor length")
    payload = signing.loads(value, salt=CURSOR_SALT)
    if not isinstance(payload, dict) or set(payload) != {"id"}:
        raise signing.BadSignature("invalid cursor payload")
    message_id = payload["id"]
    if type(message_id) is not int or not 0 <= message_id <= MAX_DATABASE_ID:
        raise signing.BadSignature("invalid cursor id")
    return message_id


def _visible_messages(user):
    """Hide both directions of a block without loading a user-controlled ID list."""
    blocked_relation = UserBlock.objects.filter(
        Q(blocker_id=user.pk, blocked_id=OuterRef("sender_id"))
        | Q(blocker_id=OuterRef("sender_id"), blocked_id=user.pk)
    )
    return (
        GlobalChatMessage.objects.select_related("sender")
        .filter(sender__is_active=True, sender__is_suspended=False)
        .annotate(_has_block=Exists(blocked_relation))
        .filter(_has_block=False)
    )


def _latest_messages(user, limit: int = INITIAL_MESSAGE_LIMIT):
    messages = list(_visible_messages(user).order_by("-id")[:limit])
    messages.reverse()
    return messages


def _render_chat(
    request: HttpRequest,
    *,
    form: GlobalChatMessageForm | None = None,
    status: int = 200,
) -> HttpResponse:
    chat_messages = _latest_messages(request.user)
    latest_id = chat_messages[-1].pk if chat_messages else 0
    response = render(
        request,
        "community/global_chat.html",
        {
            "chat_messages": chat_messages,
            "chat_cursor": _encode_cursor(latest_id),
            "form": form or GlobalChatMessageForm(),
        },
        status=status,
    )
    return _private_response(response)


@never_cache
@login_required
@require_GET
def global_chat(request: HttpRequest) -> HttpResponse:
    return _render_chat(request)


@never_cache
@login_required
@require_GET
def global_chat_messages(request: HttpRequest) -> JsonResponse:
    if not _consume_user_limit(
        request.user.pk,
        "poll",
        POLL_RATE_LIMIT,
        POLL_RATE_WINDOW,
    ):
        security_logger.warning("global_chat_poll_rate_limited actor=%s", request.user.pk)
        return _rate_limited_json(POLL_RATE_WINDOW)

    if set(request.GET) - {"cursor", "limit"}:
        return _invalid_json()
    if len(request.GET.getlist("cursor")) != 1 or len(request.GET.getlist("limit")) > 1:
        return _invalid_json()

    try:
        cursor_id = _decode_cursor(request.GET.get("cursor", ""))
        raw_limit = request.GET.get("limit", str(INITIAL_MESSAGE_LIMIT))
        if len(raw_limit) > 3:
            raise ValueError
        limit = int(raw_limit)
        if not 1 <= limit <= MAX_MESSAGE_LIMIT:
            raise ValueError
    except (signing.BadSignature, TypeError, ValueError):
        return _invalid_json()

    page = list(
        _visible_messages(request.user).filter(pk__gt=cursor_id).order_by("id")[: limit + 1]
    )
    has_more = len(page) > limit
    page = page[:limit]
    next_id = page[-1].pk if page else cursor_id

    response = JsonResponse(
        {
            "messages": [
                {
                    "id": message.pk,
                    "sender": message.sender.username,
                    "body": message.body,
                    "created_at": message.created_at.isoformat(),
                    "display_time": timezone.localtime(message.created_at).strftime(
                        "%m월 %d일 %H:%M"
                    ),
                    "is_own": message.sender_id == request.user.pk,
                }
                for message in page
            ],
            "next_cursor": _encode_cursor(next_id),
            "has_more": has_more,
        }
    )
    return _private_response(response)


@sensitive_post_parameters("body")
@never_cache
@login_required
@require_POST
def global_chat_send(request: HttpRequest) -> HttpResponse:
    body_values = request.POST.getlist("body")
    if len(body_values) != 1 or len(body_values[0]) > 1_000:
        return _private_response(
            HttpResponse(
                "메시지는 1,000자 이하로 입력해 주세요.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        )

    if not _consume_user_limit(
        request.user.pk,
        "send",
        SEND_RATE_LIMIT,
        SEND_RATE_WINDOW,
    ):
        security_logger.warning("global_chat_send_rate_limited actor=%s", request.user.pk)
        response = _private_response(
            HttpResponse(
                "메시지를 너무 빠르게 보내고 있습니다. 잠시 후 다시 시도해 주세요.",
                status=429,
                content_type="text/plain; charset=utf-8",
            )
        )
        response.headers["Retry-After"] = str(SEND_RATE_WINDOW)
        return response

    form = GlobalChatMessageForm(request.POST)
    if not form.is_valid():
        return _render_chat(request, form=form, status=400)

    GlobalChatMessage.objects.create(
        sender=request.user,
        body=form.cleaned_data["body"],
    )
    return _private_response(redirect(f"{reverse('community:global_chat')}#global-chat-thread"))
