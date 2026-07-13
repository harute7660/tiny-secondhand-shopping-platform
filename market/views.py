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
from django.db.models import Avg, OuterRef, Q, Subquery
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from accounts.models import UserBlock

from .evidence import EvidenceCaptureError, ensure_trade_evidence
from .forms import (
    ListingForm,
    MessageForm,
    ReportForm,
    ReviewForm,
    SavedSearchForm,
    TransferForm,
)
from .models import (
    MAX_EXTRA_LISTING_IMAGES,
    MAX_SAVED_SEARCHES,
    MAX_TOTAL_LISTING_IMAGES,
    Conversation,
    Favorite,
    LedgerEntry,
    Listing,
    ListingDefect,
    ListingEvent,
    ListingImage,
    Message,
    Notification,
    Report,
    ReportImageEvidence,
    Review,
    SavedSearch,
    Trade,
    Transfer,
)
from .services import (
    AUTOMATIC_LISTING_BLOCKED,
    AUTOMATIC_USER_SUSPENDED,
    MAX_IMAGE_BATCH_BYTES,
    InvalidTradeError,
    MarketServiceError,
    apply_automatic_report_threshold,
    can_users_interact,
    cancel_trade_completion,
    create_listing_event,
    ensure_wallet,
    request_trade_completion,
    respond_trade_completion,
    transfer_points,
)
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
SAVED_SEARCH_RATE_LIMIT = 30
NOTIFICATION_READ_RATE_LIMIT = 240
REVIEW_RATE_LIMIT = 10
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


def _listing_upload_error(request: HttpRequest) -> str:
    allowed_fields = {"image", "extra_images"}
    if any(field_name not in allowed_fields for field_name in request.FILES):
        return "허용되지 않은 파일 입력이 포함되어 있습니다."
    uploads = [
        upload for field_name in allowed_fields for upload in request.FILES.getlist(field_name)
    ]
    if len(uploads) > MAX_TOTAL_LISTING_IMAGES:
        return f"상품 사진은 최대 {MAX_TOTAL_LISTING_IMAGES}장까지 등록할 수 있습니다."
    total_size = sum(max(getattr(upload, "size", 0) or 0, 0) for upload in uploads)
    if total_size > MAX_IMAGE_BATCH_BYTES:
        return "대표 사진을 포함한 이미지 파일 합계는 20MB 이하여야 합니다."
    return ""


def _cleanup_new_listing_files(field_files, listing_pk) -> None:
    """Delete only request-created files, including names assigned before a failed SQL write."""
    prefix = f"listings/{listing_pk}/"
    seen = set()
    for field_file in field_files:
        name = getattr(field_file, "name", "") or ""
        if not name.startswith(prefix) or name in seen:
            continue
        seen.add(name)
        _delete_storage_file(field_file.storage, name)


def _post_fields_within(request: HttpRequest, limits: dict[str, int]) -> bool:
    return all(len(request.POST.get(name, "")) <= limit for name, limit in limits.items())


def _parse_uuid_query(value: str):
    if not value or len(value) > 36:
        raise Http404
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise Http404 from exc


def _hash_listing_image(field_file, listing_pk):
    digest = hashlib.sha256()
    try:
        with field_file.storage.open(field_file.name, "rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
    except (FileNotFoundError, OSError):
        security_logger.exception("report_snapshot_image_unavailable listing=%s", listing_pk)
        return ""
    return digest.hexdigest()


def _capture_listing_snapshot(report: Report, listing: Listing):
    report.listing_title_snapshot = listing.title
    report.listing_description_snapshot = listing.description
    report.listing_price_snapshot = listing.price_points
    report.listing_category_snapshot = listing.category
    report.listing_condition_snapshot = listing.condition
    report.listing_region_snapshot = listing.region
    report.listing_status_snapshot = listing.status
    report.listing_defect_disclosure_snapshot = listing.defect_disclosure
    report.listing_defect_details_snapshot = listing.defect_details
    report.listing_defect_codes_snapshot = ",".join(
        listing.defects.order_by("code").values_list("code", flat=True)
    )
    report.listing_image_name_snapshot = listing.image.name if listing.image else ""
    report.listing_image_sha256 = ""
    evidence = []
    if listing.image:
        report.listing_image_sha256 = _hash_listing_image(listing.image, listing.pk)
        evidence.append(
            ReportImageEvidence(
                report=report,
                storage_name=listing.image.name,
                sha256=report.listing_image_sha256,
                position=0,
            )
        )
    for extra in listing.extra_images.order_by("position"):
        evidence.append(
            ReportImageEvidence(
                report=report,
                storage_name=extra.image.name,
                sha256=_hash_listing_image(extra.image, listing.pk),
                position=extra.position,
            )
        )
    return evidence


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
    queryset = Listing.objects.select_related("seller").prefetch_related(
        "extra_images",
        "defects",
    )
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

    sort = request.GET.get("sort", "newest")
    order_by = SORT_FIELDS.get(sort)
    if order_by is None:
        sort = "newest"
        order_by = SORT_FIELDS[sort]
    listings = listings.order_by(order_by)

    page_obj = Paginator(listings, 12).get_page(request.GET.get("page"))
    saved_search_form = SavedSearchForm(
        initial={"query": query, "category": category, "region": region}
    )
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
            "saved_search_form": saved_search_form,
        },
    )


@login_required
@never_cache
@require_GET
def my_listings(request: HttpRequest) -> HttpResponse:
    listings = (
        Listing.objects.filter(seller=request.user)
        .exclude(status=Listing.Status.DELETED)
        .select_related("blocked_by")
        .order_by("-created_at")
    )
    page_obj = Paginator(listings, 20).get_page(request.GET.get("page"))
    return render(
        request,
        "market/my_listings.html",
        {"listings": page_obj.object_list, "page_obj": page_obj},
    )


@require_GET
def listing_detail(request: HttpRequest, pk) -> HttpResponse:
    listing = _detail_listing(request, pk)
    is_favorite = False
    can_contact = False
    has_pending_trade = Trade.objects.filter(
        listing=listing,
        status=Trade.Status.PENDING_BUYER,
    ).exists()
    has_completed_trade = Trade.objects.filter(
        listing=listing,
        status=Trade.Status.COMPLETED,
    ).exists()
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, listing=listing).exists()
        can_contact = (
            listing.status in CONTACTABLE_STATUSES
            and not has_completed_trade
            and can_users_interact(request.user, listing.seller, listing)
        )
    seller_completed_count = Trade.objects.filter(
        conversation__seller=listing.seller,
        status=Trade.Status.COMPLETED,
    ).count()
    seller_review_summary = Review.objects.filter(
        trade__conversation__seller=listing.seller,
        trade__status=Trade.Status.COMPLETED,
        direction=Review.Direction.BUYER_TO_SELLER,
        visibility=Review.Visibility.PUBLIC,
    ).aggregate(average=Avg("rating"))
    has_active_trade = has_pending_trade or has_completed_trade
    return render(
        request,
        "market/listing_detail.html",
        {
            "listing": listing,
            "is_favorite": is_favorite,
            "can_contact": can_contact,
            "seller_completed_count": seller_completed_count,
            "seller_average_rating": seller_review_summary["average"],
            "has_active_trade": has_active_trade,
            "has_pending_trade": has_pending_trade,
            "has_completed_trade": has_completed_trade,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def listing_create(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        upload_error = _listing_upload_error(request)
        if upload_error:
            if not _post_fields_within(
                request,
                {"title": 150, "description": 5_000, "region": 100},
            ):
                return _invalid_request()
            # Preserve safe text selections without rebinding rejected file
            # objects, so template rendering cannot trigger image decoding.
            form = ListingForm(request.POST or None)
            return render(
                request,
                "market/listing_form.html",
                {
                    "form": form,
                    "mode": "create",
                    "preflight_error": (
                        f"{upload_error} 보안을 위해 선택한 사진은 다시 골라 주세요. "
                        "제목과 설명은 그대로 유지했습니다."
                    ),
                },
                status=400,
            )
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
        additions = list(form.cleaned_data.get("extra_images") or [])
        created_field_files = []
        listing = form.save(commit=False)
        listing.seller = request.user
        listing.status = Listing.Status.ACTIVE
        if not listing.image and additions:
            listing.image = additions.pop(0)
        if listing.image:
            created_field_files.append(listing.image)
        try:
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
                    listing.full_clean(exclude=("seller", "status"))
                    listing.save()
                    ListingDefect.objects.bulk_create(
                        [
                            ListingDefect(listing=listing, code=code)
                            for code in form.cleaned_data.get("defects", ())
                        ]
                    )
                    for position, content in enumerate(additions, start=1):
                        extra = ListingImage(
                            listing=listing,
                            image=content,
                            position=position,
                        )
                        created_field_files.append(extra.image)
                        extra.save()
                    create_listing_event(listing, ListingEvent.Kind.NEW_MATCH)
                    messages.success(request, "상품이 안전하게 등록되었습니다.")
                    return redirect("market:listing_detail", pk=listing.pk)
        except Exception:
            _cleanup_new_listing_files(created_field_files, listing.pk)
            raise
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
    if Trade.objects.filter(
        listing=listing,
        status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
    ).exists():
        raise PermissionDenied
    if request.method == "POST":
        upload_error = _listing_upload_error(request)
        if upload_error:
            if not _post_fields_within(
                request,
                {"title": 150, "description": 5_000, "region": 100},
            ):
                return _invalid_request()
            form = ListingForm(
                request.POST or None,
                instance=listing,
            )
            return render(
                request,
                "market/listing_form.html",
                {
                    "form": form,
                    "listing": listing,
                    "mode": "update",
                    "preflight_error": (
                        f"{upload_error} 보안을 위해 선택한 사진은 다시 골라 주세요. "
                        "나머지 수정 내용은 그대로 유지했습니다."
                    ),
                },
                status=400,
            )
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
            {"title": 150, "description": 5_000, "region": 100, "revision": 64},
        ):
            return _invalid_request()
        revision_values = request.POST.getlist("revision")
        if len(revision_values) != 1 or not revision_values[0].strip():
            security_logger.warning(
                "listing_revision_rejected actor=%s listing=%s count=%s",
                request.user.pk,
                listing.pk,
                len(revision_values),
            )
            return _invalid_request()
    form = ListingForm(request.POST or None, request.FILES or None, instance=listing)
    if request.method == "POST" and form.is_valid():
        storage = listing.image.storage
        old_image_name = ""
        new_image_name = ""
        created_field_files = []
        deleted_files = []
        additions = list(form.cleaned_data.get("extra_images") or [])
        removal_ids = {uuid.UUID(value) for value in form.cleaned_data["remove_extra_images"]}
        try:
            with transaction.atomic():
                locked = get_object_or_404(
                    Listing.objects.select_for_update(),
                    pk=pk,
                    seller=request.user,
                )
                if locked.status not in EDITABLE_STATUSES:
                    raise PermissionDenied
                if Trade.objects.filter(
                    listing=locked,
                    status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
                ).exists():
                    raise PermissionDenied
                submitted_revision = form.cleaned_data["revision"]
                current_revision = locked.updated_at.isoformat(timespec="microseconds")
                if submitted_revision != current_revision:
                    security_logger.info(
                        "listing_stale_update_rejected actor=%s listing=%s",
                        request.user.pk,
                        locked.pk,
                    )
                    form.add_error(
                        None,
                        "다른 화면에서 이 상품이 먼저 수정되었습니다. "
                        "현재 페이지를 새로고침해 최신 내용을 확인한 뒤 다시 수정해 주세요. "
                        "브라우저 보안상 선택한 새 사진은 다시 골라야 합니다.",
                    )
                    return render(
                        request,
                        "market/listing_form.html",
                        {"form": form, "listing": locked, "mode": "update"},
                        status=409,
                    )
                old_image_name = locked.image.name if locked.image else ""
                old_price = locked.price_points
                editable_fields = (
                    "title",
                    "description",
                    "price_points",
                    "category",
                    "condition",
                    "region",
                    "defect_disclosure",
                    "defect_details",
                )
                for field_name in editable_fields:
                    setattr(locked, field_name, form.cleaned_data[field_name])
                # ClearableFileInput represents an explicit deletion as False.
                # Delegate normalization to Django's FileField instead of ever
                # assigning the boolean sentinel to the model descriptor.
                image_was_submitted = "image" in request.FILES or "image-clear" in request.POST
                if image_was_submitted:
                    Listing._meta.get_field("image").save_form_data(
                        locked,
                        form.cleaned_data["image"],
                    )
                primary_is_new = "image" in request.FILES

                current_extras = list(
                    ListingImage.objects.select_for_update()
                    .filter(listing=locked)
                    .order_by("position")
                )
                current_ids = {item.pk for item in current_extras}
                if not removal_ids.issubset(current_ids):
                    raise PermissionDenied
                remaining_extras = []
                for extra in current_extras:
                    if extra.pk in removal_ids:
                        deleted_files.append(extra.image.name)
                        extra.delete()
                    else:
                        remaining_extras.append(extra)

                if not locked.image:
                    if remaining_extras:
                        promoted = remaining_extras.pop(0)
                        locked.image.name = promoted.image.name
                        promoted.delete()
                    elif additions:
                        locked.image = additions.pop(0)
                        primary_is_new = True

                if (1 if locked.image else 0) + len(remaining_extras) + len(additions) > (
                    MAX_TOTAL_LISTING_IMAGES
                ):
                    raise PermissionDenied
                locked.full_clean(exclude=("seller", "status"))
                if primary_is_new and locked.image:
                    created_field_files.append(locked.image)
                locked.save(update_fields=(*editable_fields, "image", "updated_at"))
                new_image_name = locked.image.name if locked.image else ""

                occupied_positions = {item.position for item in remaining_extras}
                free_positions = [
                    position
                    for position in range(1, MAX_EXTRA_LISTING_IMAGES + 1)
                    if position not in occupied_positions
                ]
                if len(additions) > len(free_positions):
                    raise PermissionDenied
                for position, content in zip(free_positions, additions, strict=False):
                    extra = ListingImage(
                        listing=locked,
                        image=content,
                        position=position,
                    )
                    created_field_files.append(extra.image)
                    extra.save()

                ListingDefect.objects.filter(listing=locked).delete()
                ListingDefect.objects.bulk_create(
                    [
                        ListingDefect(listing=locked, code=code)
                        for code in form.cleaned_data.get("defects", ())
                    ]
                )
                if old_image_name and old_image_name != new_image_name:
                    deleted_files.append(old_image_name)
                for filename in dict.fromkeys(deleted_files):
                    transaction.on_commit(
                        lambda name=filename, backend=storage: _delete_storage_file(backend, name)
                    )
                if locked.price_points < old_price:
                    create_listing_event(
                        locked,
                        ListingEvent.Kind.PRICE_DROP,
                        old_price=old_price,
                    )
                listing = locked
        except Exception:
            _cleanup_new_listing_files(created_field_files, pk)
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
    if Trade.objects.filter(
        listing=listing,
        status=Trade.Status.PENDING_BUYER,
    ).exists():
        raise PermissionDenied
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
            if Trade.objects.filter(
                listing=listing,
                status=Trade.Status.PENDING_BUYER,
            ).exists():
                raise PermissionDenied
            completed_trade = (
                Trade.objects.select_for_update()
                .filter(listing=listing, status=Trade.Status.COMPLETED)
                .first()
            )
            if completed_trade is not None:
                try:
                    # Migration-safe fallback for completed rows created before
                    # trade evidence snapshots existed. Completed listings are
                    # otherwise immutable, so this still captures their sale state.
                    ensure_trade_evidence(completed_trade, listing)
                except EvidenceCaptureError:
                    security_logger.exception(
                        "trade_evidence_archive_capture_failed trade=%s listing=%s",
                        completed_trade.pk,
                        listing.pk,
                    )
                    messages.error(
                        request,
                        "거래 증거를 안전하게 보존하지 못해 상품을 숨기지 않았습니다.",
                    )
                    return redirect("market:listing_detail", pk=listing.pk)
            old_image_name = listing.image.name if listing.image else ""
            storage = listing.image.storage
            extra_image_names = list(
                ListingImage.objects.select_for_update()
                .filter(listing=listing)
                .values_list("image", flat=True)
            )
            ListingImage.objects.filter(listing=listing).delete()
            ListingDefect.objects.filter(listing=listing).delete()
            listing.status = Listing.Status.DELETED
            listing.image = ""
            # Keep the Listing row as the immutable anchor for protected
            # Trade/Review records, while removing user-authored free text and
            # location details from ordinary presentation surfaces.
            listing.title = "숨김 처리된 상품"
            listing.description = ""
            listing.region = ""
            listing.defect_disclosure = Listing.DefectDisclosure.UNKNOWN
            listing.defect_details = ""
            listing.save(
                update_fields=(
                    "status",
                    "image",
                    "title",
                    "description",
                    "region",
                    "defect_disclosure",
                    "defect_details",
                    "updated_at",
                )
            )
            for filename in dict.fromkeys([old_image_name, *extra_image_names]):
                if not filename:
                    continue
                transaction.on_commit(
                    lambda name=filename, backend=storage: _delete_storage_file(backend, name)
                )
        security_logger.info(
            "listing_soft_deleted actor=%s listing=%s", request.user.pk, listing.pk
        )
        messages.success(
            request,
            "상품을 목록에서 숨기고 공개용 설명·지역·사진 정보를 정리했습니다.",
        )
        return redirect("market:home")
    return render(request, "market/confirm_delete.html", {"listing": listing})


@login_required
@require_POST
def listing_status_update(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(request.user, "listing-state", 60, 60 * 60):
        return _rate_limited("상태 변경 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    requested_status = request.POST.get("status", "")
    allowed_transitions = {
        Listing.Status.ACTIVE: {Listing.Status.RESERVED},
        Listing.Status.RESERVED: {Listing.Status.ACTIVE},
    }
    with transaction.atomic():
        listing = get_object_or_404(
            Listing.objects.select_for_update(),
            pk=pk,
            seller=request.user,
        )
        if requested_status not in allowed_transitions.get(listing.status, set()):
            raise PermissionDenied
        if Trade.objects.filter(
            listing=listing,
            status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
        ).exists():
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


@require_GET
def listing_extra_image(request: HttpRequest, pk, image_pk) -> HttpResponse:
    listing = _detail_listing(request, pk)
    extra = get_object_or_404(ListingImage, pk=image_pk, listing=listing)
    try:
        image_file = extra.image.storage.open(extra.image.name, "rb")
    except (FileNotFoundError, OSError) as exc:
        raise Http404 from exc
    response = FileResponse(image_file, content_type="image/jpeg")
    response.headers["Content-Disposition"] = 'inline; filename="listing.jpg"'
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def favorite_toggle(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(request.user, "favorite", 120, 60 * 60):
        return _rate_limited("요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    with transaction.atomic():
        listing = get_object_or_404(
            Listing.objects.select_for_update().select_related("seller"),
            pk=pk,
            status__in=PUBLIC_STATUSES,
            seller__is_active=True,
            seller__is_suspended=False,
        )
        if not can_users_interact(request.user, listing.seller, listing):
            raise PermissionDenied
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            listing=listing,
        )
        if not created:
            favorite.delete()
            messages.info(request, "찜 목록에서 제거했습니다.")
        else:
            messages.success(request, "찜 목록에 추가했습니다.")
    return redirect("market:listing_detail", pk=listing.pk)


@login_required
@never_cache
@require_GET
def saved_search_list(request: HttpRequest) -> HttpResponse:
    searches = SavedSearch.objects.filter(user=request.user).order_by("-created_at")
    return render(
        request,
        "market/saved_search_list.html",
        {"saved_searches": searches, "form": SavedSearchForm()},
    )


@login_required
@require_POST
def saved_search_create(request: HttpRequest) -> HttpResponse:
    if not _consume_actor_limit(
        request.user,
        "saved-search",
        SAVED_SEARCH_RATE_LIMIT,
        60 * 60,
    ):
        return _rate_limited("저장 검색 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    if not _post_fields_within(request, {"query": 100, "category": 20, "region": 50}):
        return _invalid_request()

    form = SavedSearchForm(request.POST)
    if not form.is_valid():
        searches = SavedSearch.objects.filter(user=request.user).order_by("-created_at")
        return render(
            request,
            "market/saved_search_list.html",
            {"saved_searches": searches, "form": form},
            status=400,
        )

    duplicate = False
    quota_exceeded = False
    try:
        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            if SavedSearch.objects.filter(user=request.user).count() >= MAX_SAVED_SEARCHES:
                quota_exceeded = True
            else:
                saved_search = form.save(commit=False)
                saved_search.user = request.user
                saved_search.save()
    except IntegrityError:
        duplicate = True

    if quota_exceeded:
        messages.error(
            request,
            f"관심 검색 조건은 최대 {MAX_SAVED_SEARCHES}개까지 저장할 수 있습니다.",
        )
    elif duplicate:
        messages.info(request, "이미 저장한 검색 조건입니다.")
    else:
        messages.success(request, "관심 검색 조건을 저장했습니다. 이후 새 상품부터 알려드려요.")
    return redirect("market:saved_search_list")


@login_required
@require_POST
def saved_search_delete(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(
        request.user,
        "saved-search",
        SAVED_SEARCH_RATE_LIMIT,
        60 * 60,
    ):
        return _rate_limited("저장 검색 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    saved_search = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    saved_search.delete()
    messages.info(request, "관심 검색 조건을 삭제했습니다.")
    return redirect("market:saved_search_list")


@login_required
@never_cache
@require_GET
def notification_list(request: HttpRequest) -> HttpResponse:
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related("event__listing__seller", "saved_search")
        .order_by("-created_at")
    )
    page_obj = Paginator(notifications, 30).get_page(request.GET.get("page"))
    for notification in page_obj.object_list:
        notification.listing_visible = _listing_visible_to(
            request.user,
            notification.event.listing,
        )
    return render(
        request,
        "market/notification_list.html",
        {"notifications": page_obj.object_list, "page_obj": page_obj},
    )


@login_required
@require_POST
def notification_read(request: HttpRequest, pk) -> HttpResponse:
    if not _consume_actor_limit(
        request.user,
        "notification-read",
        NOTIFICATION_READ_RATE_LIMIT,
        60 * 60,
    ):
        return _rate_limited("알림 처리 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=("read_at",))
    return redirect("market:notification_list")


@login_required
@require_POST
def notification_read_all(request: HttpRequest) -> HttpResponse:
    if not _consume_actor_limit(
        request.user,
        "notification-read",
        NOTIFICATION_READ_RATE_LIMIT,
        60 * 60,
    ):
        return _rate_limited("알림 처리 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(
        read_at=timezone.now()
    )
    return redirect("market:notification_list")


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
    if Trade.objects.filter(listing=listing, status=Trade.Status.COMPLETED).exists():
        raise PermissionDenied
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
    listing_active_trade = (
        Trade.objects.filter(
            listing=conversation.listing,
            status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
        )
        .prefetch_related("reviews")
        .order_by("-created_at")
        .first()
    )
    active_trade = (
        listing_active_trade
        if listing_active_trade and listing_active_trade.conversation_id == conversation.pk
        else None
    )
    other_active_trade_exists = bool(listing_active_trade and active_trade is None)
    recent_closed_trade = (
        Trade.objects.filter(
            conversation=conversation,
            status__in=(Trade.Status.REJECTED, Trade.Status.CANCELLED),
        )
        .order_by("-created_at")
        .first()
        if active_trade is None
        else None
    )
    review_direction = (
        Review.Direction.BUYER_TO_SELLER
        if request.user.pk == conversation.buyer_id
        else Review.Direction.SELLER_TO_BUYER
    )
    has_reviewed = bool(
        active_trade
        and active_trade.status == Trade.Status.COMPLETED
        and active_trade.reviews.filter(direction=review_direction).exists()
    )
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
            "active_trade": active_trade,
            "other_active_trade_exists": other_active_trade_exists,
            "recent_closed_trade": recent_closed_trade,
            "has_reviewed": has_reviewed,
        },
    )


@login_required
@require_POST
def trade_request_completion(request: HttpRequest, pk) -> HttpResponse:
    conversation = get_object_or_404(
        Conversation,
        pk=pk,
        seller=request.user,
    )
    if not _consume_actor_limit(request.user, "trade-completion", 30, 60 * 60):
        return _rate_limited("거래 완료 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    try:
        request_trade_completion(request.user, conversation.pk)
    except InvalidTradeError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, "구매자에게 거래 완료 확인을 요청했습니다.")
    return redirect("market:conversation_detail", pk=conversation.pk)


@login_required
@require_POST
def trade_confirm(request: HttpRequest, pk) -> HttpResponse:
    trade = get_object_or_404(Trade, pk=pk, conversation__buyer=request.user)
    if not _consume_actor_limit(request.user, "trade-completion", 30, 60 * 60):
        return _rate_limited("거래 완료 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    try:
        respond_trade_completion(request.user, trade.pk, approve=True)
    except InvalidTradeError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.success(request, "양측 확인이 완료되었습니다. 이제 서로 후기를 남길 수 있어요.")
    return redirect("market:conversation_detail", pk=trade.conversation_id)


@login_required
@require_POST
def trade_reject(request: HttpRequest, pk) -> HttpResponse:
    trade = get_object_or_404(Trade, pk=pk, conversation__buyer=request.user)
    if not _consume_actor_limit(request.user, "trade-completion", 30, 60 * 60):
        return _rate_limited("거래 완료 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    try:
        respond_trade_completion(request.user, trade.pk, approve=False)
    except InvalidTradeError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.info(request, "거래 완료 요청을 거절했습니다.")
    return redirect("market:conversation_detail", pk=trade.conversation_id)


@login_required
@require_POST
def trade_cancel(request: HttpRequest, pk) -> HttpResponse:
    trade = get_object_or_404(Trade, pk=pk, conversation__seller=request.user)
    if not _consume_actor_limit(request.user, "trade-completion", 30, 60 * 60):
        return _rate_limited("거래 완료 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    try:
        cancel_trade_completion(request.user, trade.pk)
    except InvalidTradeError as exc:
        messages.error(request, exc.messages[0])
    else:
        messages.info(request, "거래 완료 요청을 취소했습니다.")
    return redirect("market:conversation_detail", pk=trade.conversation_id)


@login_required
@never_cache
@require_http_methods(["GET", "POST"])
def review_create(request: HttpRequest, pk) -> HttpResponse:
    trade = get_object_or_404(
        Trade.objects.select_related("conversation__buyer", "conversation__seller", "listing"),
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        pk=pk,
        status=Trade.Status.COMPLETED,
    )
    direction = (
        Review.Direction.BUYER_TO_SELLER
        if request.user.pk == trade.conversation.buyer_id
        else Review.Direction.SELLER_TO_BUYER
    )
    if Review.objects.filter(trade=trade, direction=direction).exists():
        messages.info(request, "이미 이 거래의 후기를 작성했습니다.")
        return redirect("market:conversation_detail", pk=trade.conversation_id)
    if request.method == "POST":
        if not _consume_actor_limit(
            request.user,
            "review-create",
            REVIEW_RATE_LIMIT,
            60 * 60 * 24,
        ):
            return _rate_limited("후기 작성 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        if not _post_fields_within(request, {"rating": 2, "body": 500}):
            return _invalid_request()
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        duplicate = False
        try:
            with transaction.atomic():
                locked_trade = get_object_or_404(
                    Trade.objects.select_for_update().select_related("conversation"),
                    Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
                    pk=trade.pk,
                    status=Trade.Status.COMPLETED,
                )
                review = form.save(commit=False)
                review.trade = locked_trade
                review.direction = direction
                review.full_clean()
                review.save()
                if locked_trade.reviews.count() == 2:
                    locked_trade.reviews.filter(
                        visibility=Review.Visibility.PENDING,
                    ).update(visibility=Review.Visibility.PUBLIC)
        except IntegrityError:
            duplicate = True
        if duplicate:
            messages.info(request, "이미 이 거래의 후기를 작성했습니다.")
        else:
            security_logger.info("review_created actor=%s trade=%s", request.user.pk, trade.pk)
            messages.success(
                request,
                "거래 후기를 등록했습니다. 양쪽 후기가 모두 제출되면 함께 공개됩니다.",
            )
        return redirect("market:conversation_detail", pk=trade.conversation_id)
    counterpart = (
        trade.conversation.seller
        if request.user.pk == trade.conversation.buyer_id
        else trade.conversation.buyer
    )
    return render(
        request,
        "market/review_form.html",
        {"form": form, "trade": trade, "counterpart": counterpart},
        status=400 if request.method == "POST" else 200,
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
    if url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
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
        moderation_outcome = None
        try:
            with transaction.atomic():
                # Serialize a reporter's duplicate/daily-limit checks and, for
                # listing reports, serialize the evidence snapshot against
                # seller edits and deletion. User-report pairs are locked in
                # primary-key order to avoid A-reports-B/B-reports-A deadlocks.
                user_model = get_user_model()
                if target_listing is not None:
                    user_model.objects.select_for_update().get(pk=request.user.pk)
                    target_listing = get_object_or_404(
                        Listing.objects.select_for_update().select_related("seller"),
                        pk=target_listing.pk,
                        status__in=PUBLIC_STATUSES,
                        seller__is_active=True,
                        seller__is_suspended=False,
                    )
                    duplicate_filter = {"listing": target_listing}
                else:
                    locked_users = {
                        user.pk: user
                        for user in user_model.objects.select_for_update()
                        .filter(pk__in=(request.user.pk, target_user.pk))
                        .order_by("pk")
                    }
                    target_user = locked_users.get(target_user.pk)
                    if target_user is None:
                        raise Http404
                    duplicate_filter = {"target_user": target_user}

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
                    image_evidence = []
                    if target_listing is not None:
                        image_evidence = _capture_listing_snapshot(report, target_listing)
                    report.full_clean()
                    report.save()
                    if image_evidence:
                        ReportImageEvidence.objects.bulk_create(image_evidence)
                    moderation_outcome = apply_automatic_report_threshold(report)
        except IntegrityError:
            form_error = "이미 검토 중인 신고가 있습니다."

        if form_error:
            form.add_error(None, form_error)
        elif report is not None:
            security_logger.info("report_created actor=%s report=%s", request.user.pk, report.pk)
            messages.success(request, "신고가 접수되었습니다. 관리자가 검토합니다.")
            if moderation_outcome == AUTOMATIC_LISTING_BLOCKED:
                messages.warning(
                    request,
                    "여러 사용자의 신고가 확인되어 해당 상품을 임시 비공개 처리했습니다.",
                )
                return redirect("market:home")
            if moderation_outcome == AUTOMATIC_USER_SUSPENDED:
                messages.warning(
                    request,
                    "여러 사용자의 신고가 확인되어 상대 계정을 임시 정지했습니다.",
                )
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
