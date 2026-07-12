from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import OuterRef, Q, Subquery
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import UserBlock

from .forms import ListingForm, MessageForm, ReportForm, TransferForm
from .models import Conversation, Favorite, LedgerEntry, Listing, Message, Report, Transfer
from .services import MarketServiceError, can_users_interact, ensure_wallet, transfer_points
from .storage import delete_listing_image_unless_evidence

security_logger = logging.getLogger("tiny_market.security")
PUBLIC_STATUSES = (Listing.Status.ACTIVE, Listing.Status.RESERVED, Listing.Status.SOLD)
CONTACTABLE_STATUSES = (Listing.Status.ACTIVE, Listing.Status.RESERVED)
EDITABLE_STATUSES = (Listing.Status.ACTIVE, Listing.Status.RESERVED)
MAX_LISTINGS_PER_ACCOUNT = 50
MAX_LISTING_HISTORY_PER_ACCOUNT = 500
LISTING_RATE_LIMIT = 10
LISTING_RATE_WINDOW = 60 * 60
LISTING_UPDATE_RATE_LIMIT = 30
SORT_FIELDS = {
    "newest": "-created_at",
    "oldest": "created_at",
    "price_low": "price_points",
    "price_high": "-price_points",
}


def _delete_storage_file(storage, name: str) -> None:
    delete_listing_image_unless_evidence(storage, name)


def _consume_actor_limit(user, action: str, limit: int, timeout: int) -> bool:
    """Use an atomic cache increment; production must configure a shared cache."""
    key = f"tiny-market:{action}:user:{user.pk}"
    if cache.add(key, 1, timeout=timeout):
        return True
    try:
        return cache.incr(key) <= limit
    except ValueError:
        return cache.add(key, 1, timeout=timeout)


def _rate_limited(message: str) -> HttpResponse:
    return HttpResponse(message, status=429, content_type="text/plain; charset=utf-8")


def _invalid_request() -> HttpResponse:
    return HttpResponse(
        "입력값을 확인해 주세요.",
        status=400,
        content_type="text/plain; charset=utf-8",
    )


def _post_fields_within(request: HttpRequest, limits: dict[str, int]) -> bool:
    return all(len(request.POST.get(name, "")) <= limit for name, limit in limits.items())


def _parse_uuid_query(value: str):
    if not value or len(value) > 36:
        raise Http404
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise Http404 from exc


def _capture_listing_snapshot(report: Report, listing: Listing) -> None:
    report.listing_title_snapshot = listing.title
    report.listing_description_snapshot = listing.description
    report.listing_price_snapshot = listing.price_points
    report.listing_category_snapshot = listing.category
    report.listing_condition_snapshot = listing.condition
    report.listing_region_snapshot = listing.region
    report.listing_status_snapshot = listing.status
    report.listing_image_name_snapshot = listing.image.name if listing.image else ""
    report.listing_image_sha256 = ""
    if not listing.image:
        return
    digest = hashlib.sha256()
    try:
        with listing.image.storage.open(listing.image.name, "rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
    except (FileNotFoundError, OSError):
        security_logger.exception(
            "report_snapshot_image_unavailable listing=%s",
            listing.pk,
        )
        return
    report.listing_image_sha256 = digest.hexdigest()


def _listing_visible_to(user, listing: Listing) -> bool:
    if user.is_authenticated and user.has_perm("market.view_listing"):
        return True
    if user.is_authenticated and listing.seller_id == user.pk:
        return True
    return (
        listing.status in PUBLIC_STATUSES
        and listing.seller.is_active
        and not listing.seller.is_suspended
    )


def _detail_listing(request: HttpRequest, pk) -> Listing:
    queryset = Listing.objects.select_related("seller")
    if request.user.is_authenticated and request.user.has_perm("market.view_listing"):
        return get_object_or_404(queryset, pk=pk)
    if request.user.is_authenticated:
        queryset = queryset.filter(
            Q(seller=request.user)
            | Q(
                status__in=PUBLIC_STATUSES,
                seller__is_active=True,
                seller__is_suspended=False,
            )
        )
    else:
        queryset = queryset.filter(
            status__in=PUBLIC_STATUSES,
            seller__is_active=True,
            seller__is_suspended=False,
        )
    return get_object_or_404(queryset, pk=pk)


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    listings = Listing.objects.filter(
        status__in=PUBLIC_STATUSES,
        seller__is_active=True,
        seller__is_suspended=False,
    ).select_related("seller")

    raw_query = request.GET.get("q", "").strip()
    if len(raw_query) > 100:
        messages.error(request, "검색어는 100자 이하로 입력해 주세요.")
        query = ""
    else:
        query = raw_query
    if query:
        listings = listings.filter(
            Q(title__icontains=query) | Q(description__icontains=query) | Q(region__icontains=query)
        )

    category = request.GET.get("category", "")
    valid_categories = {value for value, _label in Listing.Category.choices}
    if category in valid_categories:
        listings = listings.filter(category=category)
    else:
        category = ""

    status = request.GET.get("status", "")
    if status in PUBLIC_STATUSES:
        listings = listings.filter(status=status)
    else:
        status = ""

    region = request.GET.get("region", "").strip()
    if len(region) > 50:
        messages.error(request, "지역 필터는 50자 이하로 입력해 주세요.")
        region = ""
    if region:
        listings = listings.filter(region__icontains=region)

    if request.GET.get("mine") == "1" and request.user.is_authenticated:
        listings = (
            Listing.objects.filter(seller=request.user)
            .exclude(status=Listing.Status.DELETED)
            .select_related("seller")
        )

    sort = request.GET.get("sort", "newest")
    order_by = SORT_FIELDS.get(sort)
    if order_by is None:
        sort = "newest"
        order_by = SORT_FIELDS[sort]
    listings = listings.order_by(order_by)

    page_obj = Paginator(listings, 12).get_page(request.GET.get("page"))
    return render(
        request,
        "home.html",
        {
            "listings": page_obj.object_list,
            "page_obj": page_obj,
            "categories": Listing.Category.choices,
            "statuses": [
                (value, label)
                for value, label in Listing.Status.choices
                if value in PUBLIC_STATUSES
            ],
            "query": query,
            "selected_category": category,
            "selected_status": status,
            "selected_region": region,
            "selected_sort": sort,
        },
    )


@require_GET
def listing_detail(request: HttpRequest, pk) -> HttpResponse:
    listing = _detail_listing(request, pk)
    is_favorite = False
    can_contact = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, listing=listing).exists()
        can_contact = can_users_interact(request.user, listing.seller, listing)
    seller_completed_count = Listing.objects.filter(
        seller=listing.seller, status=Listing.Status.SOLD
    ).count()
    return render(
        request,
        "market/listing_detail.html",
        {
            "listing": listing,
            "is_favorite": is_favorite,
            "can_contact": can_contact,
            "seller_completed_count": seller_completed_count,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def listing_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        if not _consume_actor_limit(
            request.user,
            "listing-create",
            LISTING_RATE_LIMIT,
            LISTING_RATE_WINDOW,
        ):
            return _rate_limited("상품 등록 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if request.FILES and not _consume_actor_limit(
            request.user,
            "listing-image",
            10,
            LISTING_RATE_WINDOW,
        ):
            return _rate_limited("이미지 처리 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if not _post_fields_within(
            request,
            {"title": 150, "description": 5_000, "region": 100},
        ):
            return _invalid_request()
    form = ListingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            # Serialize quota checks per account on databases with row locking.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            current_count = (
                Listing.objects.filter(seller=request.user)
                .exclude(status=Listing.Status.DELETED)
                .count()
            )
            history_count = Listing.objects.filter(seller=request.user).count()
            if (
                current_count >= MAX_LISTINGS_PER_ACCOUNT
                or history_count >= MAX_LISTING_HISTORY_PER_ACCOUNT
            ):
                form.add_error(None, "계정당 보관 가능한 상품 수를 초과했습니다.")
            else:
                listing = form.save(commit=False)
                listing.seller = request.user
                listing.status = Listing.Status.ACTIVE
                listing.save()
                messages.success(request, "상품이 안전하게 등록되었습니다.")
                return redirect("market:listing_detail", pk=listing.pk)
    return render(request, "market/listing_form.html", {"form": form, "mode": "create"})


@login_required
@require_http_methods(["GET", "POST"])
def listing_update(request: HttpRequest, pk) -> HttpResponse:
    listing = get_object_or_404(
        Listing,
        pk=pk,
        seller=request.user,
        status__in=EDITABLE_STATUSES,
    )
    if request.method == "POST":
        if not _consume_actor_limit(
            request.user,
            "listing-update",
            LISTING_UPDATE_RATE_LIMIT,
            LISTING_RATE_WINDOW,
        ):
            return _rate_limited("상품 수정 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if request.FILES and not _consume_actor_limit(
            request.user,
            "listing-image",
            10,
            LISTING_RATE_WINDOW,
        ):
            return _rate_limited("이미지 처리 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if not _post_fields_within(
            request,
            {"title": 150, "description": 5_000, "region": 100},
        ):
            return _invalid_request()
    form = ListingForm(request.POST or None, request.FILES or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        storage = listing.image.storage
        old_image_name = ""
        new_image_name = ""
        try:
            with transaction.atomic():
                locked = get_object_or_404(
                    Listing.objects.select_for_update(),
                    pk=pk,
                    seller=request.user,
                )
                if locked.status not in EDITABLE_STATUSES:
                    raise PermissionDenied
                old_image_name = locked.image.name if locked.image else ""
                editable_fields = (
                    "title",
                    "description",
                    "price_points",
                    "category",
                    "condition",
                    "region",
                    "image",
                )
                for field_name in editable_fields:
                    setattr(locked, field_name, form.cleaned_data[field_name])
                locked.full_clean(exclude=("seller", "status"))
                locked.save(update_fields=(*editable_fields, "updated_at"))
                new_image_name = locked.image.name if locked.image else ""
                if old_image_name and old_image_name != new_image_name:
                    transaction.on_commit(
                        lambda name=old_image_name, backend=storage: _delete_storage_file(
                            backend, name
                        )
                    )
                listing = locked
        except Exception:
            if new_image_name and new_image_name != old_image_name:
                _delete_storage_file(storage, new_image_name)
            raise
        messages.success(request, "상품 정보가 수정되었습니다.")
        return redirect("market:listing_detail", pk=listing.pk)
    return render(
        request,
        "market/listing_form.html",
        {"form": form, "listing": listing, "mode": "update"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def listing_delete(request: HttpRequest, pk) -> HttpResponse:
    listing = get_object_or_404(
        Listing.objects.exclude(status__in=(Listing.Status.BLOCKED, Listing.Status.DELETED)),
        pk=pk,
        seller=request.user,
    )
    if request.method == "POST":
        if not _consume_actor_limit(request.user, "listing-state", 60, 60 * 60):
            return _rate_limited("상태 변경 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        with transaction.atomic():
            listing = get_object_or_404(
                Listing.objects.select_for_update(),
                pk=pk,
                seller=request.user,
            )
            if listing.status in (Listing.Status.BLOCKED, Listing.Status.DELETED):
                raise PermissionDenied
            old_image_name = listing.image.name if listing.image else ""
            storage = listing.image.storage
            listing.status = Listing.Status.DELETED
            listing.image = ""
            listing.save(update_fields=("status", "image", "updated_at"))
            if old_image_name:
                transaction.on_commit(
                    lambda name=old_image_name, backend=storage: _delete_storage_file(backend, name)
                )
        security_logger.info(
            "listing_soft_deleted actor=%s listing=%s", request.user.pk, listing.pk
        )
        messages.success(request, "상품이 목록에서 삭제되었습니다.")
        return redirect("market:home")
    return render(request, "market/confirm_delete.html", {"listing": listing})


@login_required
@require_POST
def listing_status_update(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(request.user, "listing-state", 60, 60 * 60):
        return _rate_limited("상태 변경 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    requested_status = request.POST.get("status", "")
    allowed_transitions = {
        Listing.Status.ACTIVE: {Listing.Status.RESERVED, Listing.Status.SOLD},
        Listing.Status.RESERVED: {Listing.Status.ACTIVE, Listing.Status.SOLD},
        Listing.Status.SOLD: {Listing.Status.ACTIVE},
    }
    with transaction.atomic():
        listing = get_object_or_404(
            Listing.objects.select_for_update(),
            pk=pk,
            seller=request.user,
        )
        if requested_status not in allowed_transitions.get(listing.status, set()):
            raise PermissionDenied
        listing.status = requested_status
        listing.save(update_fields=("status", "updated_at"))
    security_logger.info(
        "listing_status_changed actor=%s listing=%s status=%s",
        request.user.pk,
        listing.pk,
        requested_status,
    )
    messages.success(request, "판매 상태가 변경되었습니다.")
    return redirect("market:listing_detail", pk=listing.pk)


@require_GET
def listing_image(request: HttpRequest, pk) -> HttpResponse:
    listing = _detail_listing(request, pk)
    if not listing.image:
        raise Http404
    try:
        image_file = listing.image.storage.open(listing.image.name, "rb")
    except (FileNotFoundError, OSError) as exc:
        raise Http404 from exc
    response = FileResponse(image_file, content_type="image/jpeg")
    response.headers["Content-Disposition"] = 'inline; filename="listing.jpg"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    # A stable image URL must not remain in a shared cache after moderation.
    response.headers["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def favorite_toggle(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(request.user, "favorite", 120, 60 * 60):
        return _rate_limited("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status__in=PUBLIC_STATUSES,
        seller__is_active=True,
        seller__is_suspended=False,
    )
    favorite, created = Favorite.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        favorite.delete()
        messages.info(request, "찜 목록에서 제거했습니다.")
    else:
        messages.success(request, "찜 목록에 추가했습니다.")
    return redirect("market:listing_detail", pk=listing.pk)


@login_required
@require_POST
def conversation_start(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(request.user, "conversation-start", 60, 60 * 60):
        return _rate_limited("대화 시작 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status__in=CONTACTABLE_STATUSES,
        seller__is_active=True,
        seller__is_suspended=False,
    )
    if not can_users_interact(request.user, listing.seller, listing):
        raise PermissionDenied
    conversation, _created = Conversation.objects.get_or_create(
        listing=listing,
        buyer=request.user,
        defaults={"seller": listing.seller},
    )
    return redirect("market:conversation_detail", pk=conversation.pk)


@login_required
@never_cache
@require_GET
def conversation_list(request: HttpRequest) -> HttpResponse:
    last_message = Message.objects.filter(conversation=OuterRef("pk")).order_by(
        "-created_at", "-pk"
    )
    conversations = (
        Conversation.objects.filter(Q(buyer=request.user) | Q(seller=request.user))
        .select_related("listing", "buyer", "seller")
        .annotate(
            last_message_body=Subquery(last_message.values("body")[:1]),
            last_message_sender=Subquery(last_message.values("sender__username")[:1]),
        )
        .order_by("-updated_at")
    )
    page_obj = Paginator(conversations, 30).get_page(request.GET.get("page"))
    for conversation in page_obj.object_list:
        conversation.listing_visible = _listing_visible_to(request.user, conversation.listing)
    return render(
        request,
        "market/conversation_list.html",
        {"conversations": page_obj.object_list, "page_obj": page_obj},
    )


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def conversation_detail(request: HttpRequest, pk) -> HttpResponse:
    conversation = get_object_or_404(
        Conversation.objects.select_related("listing", "buyer", "seller"),
        Q(buyer=request.user) | Q(seller=request.user),
        pk=pk,
    )
    counterpart = (
        conversation.seller if request.user.pk == conversation.buyer_id else conversation.buyer
    )
    interaction_allowed = can_users_interact(request.user, counterpart, conversation.listing)
    listing_visible = _listing_visible_to(request.user, conversation.listing)

    if request.method == "POST":
        within_minute = _consume_actor_limit(request.user, "message-minute", 20, 60)
        within_day = _consume_actor_limit(
            request.user,
            "message-day",
            500,
            60 * 60 * 24,
        )
        if not within_minute or not within_day:
            return _rate_limited(
                "메시지를 너무 빠르게 보내고 있습니다. 잠시 후 다시 시도해 주세요."
            )
        if not _post_fields_within(request, {"body": 1_000}):
            return _invalid_request()
    form = MessageForm(request.POST or None)
    if request.method == "POST":
        if not interaction_allowed:
            raise PermissionDenied
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.full_clean()
            message.save()
            Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
            return redirect("market:conversation_detail", pk=conversation.pk)

    latest_messages = list(
        conversation.messages.select_related("sender").order_by("-created_at", "-pk")[:100]
    )
    latest_messages.reverse()
    return render(
        request,
        "market/conversation_detail.html",
        {
            "conversation": conversation,
            "conversation_messages": latest_messages,
            "counterpart": counterpart,
            "form": form,
            "interaction_allowed": interaction_allowed,
            "listing_visible": listing_visible,
            "is_blocking": UserBlock.objects.filter(
                blocker=request.user, blocked=counterpart
            ).exists(),
        },
    )


@login_required
@require_POST
def user_block_toggle(request: HttpRequest, user_id: int) -> HttpResponse:
    if not _consume_actor_limit(request.user, "user-block", 60, 60 * 60):
        return _rate_limited("차단 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    user_model = get_user_model()
    target = get_object_or_404(user_model, pk=user_id)
    if target.pk == request.user.pk:
        raise PermissionDenied
    has_conversation = Conversation.objects.filter(
        Q(buyer=request.user, seller=target) | Q(buyer=target, seller=request.user)
    ).exists()
    if not has_conversation:
        raise Http404
    block, created = UserBlock.objects.get_or_create(blocker=request.user, blocked=target)
    if created:
        security_logger.info("user_blocked actor=%s target=%s", request.user.pk, target.pk)
        messages.success(request, "해당 사용자를 차단했습니다.")
    else:
        block.delete()
        messages.info(request, "사용자 차단을 해제했습니다.")
    next_url = request.POST.get("next", "")
    if next_url.startswith("/") and not next_url.startswith("//"):
        return redirect(next_url)
    return redirect("market:conversation_list")


@login_required
@require_http_methods(["GET", "POST"])
def report_create(request: HttpRequest) -> HttpResponse:
    listing_value = request.GET.get("listing", "")
    conversation_value = request.GET.get("conversation", "")
    if bool(listing_value) == bool(conversation_value):
        raise Http404
    if request.method == "POST":
        if not _consume_actor_limit(request.user, "report", 10, 60 * 60 * 24):
            return _rate_limited("하루 신고 한도를 초과했습니다.")
        if not _post_fields_within(request, {"category": 20, "details": 2_000}):
            return _invalid_request()

    target_listing = None
    target_user = None
    target_conversation = None
    if listing_value:
        listing_id = _parse_uuid_query(listing_value)
        target_listing = get_object_or_404(
            Listing.objects.select_related("seller"),
            pk=listing_id,
            status__in=PUBLIC_STATUSES,
            seller__is_active=True,
            seller__is_suspended=False,
        )
        if target_listing.seller_id == request.user.pk:
            raise PermissionDenied
        duplicate_filter = {"listing": target_listing}
    else:
        conversation_id = _parse_uuid_query(conversation_value)
        target_conversation = get_object_or_404(
            Conversation.objects.select_related("buyer", "seller"),
            Q(buyer=request.user) | Q(seller=request.user),
            pk=conversation_id,
        )
        target_user = (
            target_conversation.seller
            if target_conversation.buyer_id == request.user.pk
            else target_conversation.buyer
        )
        if target_user.pk == request.user.pk:
            raise PermissionDenied
        duplicate_filter = {"target_user": target_user}

    form = ReportForm(request.POST or None)
    # ModelForm calls Report.clean() during is_valid(). Bind the server-selected
    # target first so a client cannot choose or replace the report target.
    form.instance.reporter = request.user
    form.instance.target_user = target_user
    form.instance.listing = target_listing
    if request.method == "POST" and form.is_valid():
        report = None
        form_error = None
        try:
            with transaction.atomic():
                # Serialize a reporter's duplicate/daily-limit checks and, for
                # listing reports, serialize the evidence snapshot against
                # seller edits and deletion.
                get_user_model().objects.select_for_update().get(pk=request.user.pk)
                if target_listing is not None:
                    target_listing = get_object_or_404(
                        Listing.objects.select_for_update().select_related("seller"),
                        pk=target_listing.pk,
                        status__in=PUBLIC_STATUSES,
                        seller__is_active=True,
                        seller__is_suspended=False,
                    )
                    duplicate_filter = {"listing": target_listing}

                if Report.objects.filter(
                    reporter=request.user,
                    status=Report.Status.OPEN,
                    **duplicate_filter,
                ).exists():
                    form_error = "이미 검토 중인 신고가 있습니다."
                elif (
                    Report.objects.filter(
                        reporter=request.user,
                        created_at__gte=timezone.now() - timedelta(days=1),
                    ).count()
                    >= 10
                ):
                    form_error = "하루 신고 한도를 초과했습니다."
                else:
                    report = form.save(commit=False)
                    report.reporter = request.user
                    report.target_user = target_user
                    report.listing = target_listing
                    if target_listing is not None:
                        _capture_listing_snapshot(report, target_listing)
                    report.full_clean()
                    report.save()
        except IntegrityError:
            form_error = "이미 검토 중인 신고가 있습니다."

        if form_error:
            form.add_error(None, form_error)
        elif report is not None:
            security_logger.info("report_created actor=%s report=%s", request.user.pk, report.pk)
            messages.success(request, "신고가 접수되었습니다. 관리자가 검토합니다.")
            return (
                redirect("market:listing_detail", pk=target_listing.pk)
                if target_listing
                else redirect("market:conversation_detail", pk=target_conversation.pk)
            )

    target = target_listing or target_user
    return render(
        request,
        "market/report_form.html",
        {
            "form": form,
            "target": target,
            "listing": target_listing,
            "target_user": target_user,
            "target_conversation": target_conversation,
        },
    )


@login_required
@never_cache
@require_GET
def wallet(request: HttpRequest) -> HttpResponse:
    wallet_account = ensure_wallet(request.user)
    transfers = (
        Transfer.objects.filter(
            Q(sender_account=wallet_account) | Q(receiver_account=wallet_account)
        )
        .select_related("sender_account__owner", "receiver_account__owner", "initiated_by")
        .order_by("-created_at")[:100]
    )
    ledger = LedgerEntry.objects.filter(account=wallet_account).select_related("transfer")[:100]
    return render(
        request,
        "market/wallet.html",
        {"wallet": wallet_account, "transfers": transfers, "ledger": ledger},
    )


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def transfer(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        within_minute = _consume_actor_limit(request.user, "transfer-minute", 10, 60)
        within_day = _consume_actor_limit(
            request.user,
            "transfer-day",
            200,
            60 * 60 * 24,
        )
        if not within_minute or not within_day:
            return _rate_limited("송금 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if not _post_fields_within(request, {"recipient_username": 150, "amount": 20}):
            return _invalid_request()
    wallet_account = ensure_wallet(request.user)
    initial = {}
    recipient_hint = request.GET.get("to", "")
    if len(recipient_hint) <= 150:
        initial["recipient_username"] = recipient_hint.strip()
    form = TransferForm(request.POST or None, actor=request.user, initial=initial)

    if request.method == "POST" and form.is_valid():
        try:
            posted = transfer_points(
                request.user,
                form.cleaned_data["recipient"],
                form.cleaned_data["amount"],
                form.cleaned_data["idempotency_key"],
            )
        except MarketServiceError as exc:
            form.add_error(None, exc.messages[0] if exc.messages else "송금할 수 없습니다.")
        else:
            security_logger.info(
                "demo_transfer_posted actor=%s transfer=%s", request.user.pk, posted.pk
            )
            messages.success(request, "DEMO POINT 송금이 완료되었습니다.")
            return redirect("market:wallet")

    return render(
        request,
        "market/transfer.html",
        {"form": form, "wallet": wallet_account},
    )


@require_GET
def safety(request: HttpRequest) -> HttpResponse:
    return render(request, "market/safety.html")
