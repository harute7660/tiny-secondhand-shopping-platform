import hashlib
import hmac
import io
import logging

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models import (
    AUTOMATIC_LISTING_BLOCK_REASON,
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
    WalletAccount,
)
from .services import MAX_IMAGE_BYTES, process_listing_image
from .storage import delete_listing_image_unless_evidence

security_logger = logging.getLogger("tiny_market.security")


class ListingAdminForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = (
            "title",
            "description",
            "price_points",
            "category",
            "condition",
            "region",
            "image",
        )

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if isinstance(image, UploadedFile):
            return process_listing_image(image)
        if image is False and self.instance.pk and self.instance.extra_images.exists():
            raise forms.ValidationError(
                "추가 사진이 있는 상품의 대표 사진은 관리자 화면에서 삭제할 수 없습니다."
            )
        return image


class ReadOnlyAdminMixin:
    """Expose server-authored records without allowing history rewrites."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.concrete_fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class ImmutableLedgerAdminMixin(ReadOnlyAdminMixin):
    """Expose financial records for audit without allowing history rewrites."""


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    form = ListingAdminForm
    editable_fields = ListingAdminForm.Meta.fields
    list_display = (
        "title",
        "seller",
        "price_points",
        "category",
        "condition",
        "status",
        "created_at",
    )
    list_filter = ("status", "category", "condition", "created_at")
    search_fields = ("title", "description", "seller__username", "region")
    readonly_fields = (
        "id",
        "seller",
        "status",
        "blocked_by",
        "blocked_reason",
        "created_at",
        "updated_at",
        "blocked_at",
        "defect_disclosure",
        "defect_details",
    )
    list_select_related = ("seller", "blocked_by")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("market.purge_listing") and super().has_delete_permission(
            request, obj
        )

    @staticmethod
    def _require_purge_permission(request):
        if not (
            request.user.has_perm("market.purge_listing")
            and request.user.has_perm("market.delete_listing")
        ):
            raise PermissionDenied

    @staticmethod
    def _delete_image(storage, name):
        delete_listing_image_unless_evidence(storage, name)

    def save_model(self, request, obj, form, change):
        old_name = ""
        new_name = ""
        storage = obj.image.storage
        try:
            with transaction.atomic():
                if change:
                    previous = Listing.objects.select_for_update().filter(pk=obj.pk).first()
                    if previous is None:
                        raise PermissionDenied
                    if form is None:
                        raise PermissionDenied
                    # Continue with the locked row itself so that validation/save
                    # failures also expose the new uploaded filename to cleanup.
                    obj = previous
                    stale_protected_state = (
                        previous.seller_id != form.instance.seller_id
                        or previous.status != form.instance.status
                        or previous.blocked_by_id != form.instance.blocked_by_id
                        or previous.blocked_reason != form.instance.blocked_reason
                        or previous.blocked_at != form.instance.blocked_at
                    )
                    if stale_protected_state:
                        raise PermissionDenied
                    old_name = previous.image.name if previous.image else ""
                    for field_name in self.editable_fields:
                        if field_name == "image":
                            Listing._meta.get_field("image").save_form_data(
                                previous,
                                form.cleaned_data[field_name],
                            )
                        else:
                            setattr(previous, field_name, form.cleaned_data[field_name])
                    previous.full_clean()
                    previous.save(update_fields=(*self.editable_fields, "updated_at"))
                else:
                    super().save_model(request, obj, form, change)
                new_name = obj.image.name if obj.image else ""
                if old_name and old_name != new_name:
                    transaction.on_commit(
                        lambda name=old_name, backend=storage: self._delete_image(
                            backend,
                            name,
                        )
                    )
        except Exception:
            failed_name = obj.image.name if obj.image else new_name
            if failed_name and failed_name != old_name:
                self._delete_image(storage, failed_name)
            raise

    def delete_model(self, request, obj):
        self._require_purge_permission(request)
        image_names = [obj.image.name] if obj.image else []
        image_names.extend(obj.extra_images.values_list("image", flat=True))
        storage = obj.image.storage
        super().delete_model(request, obj)
        for image_name in image_names:
            transaction.on_commit(
                lambda name=image_name, backend=storage: self._delete_image(backend, name)
            )

    def delete_queryset(self, request, queryset):
        self._require_purge_permission(request)
        files = []
        for item in queryset.prefetch_related("extra_images"):
            if item.image:
                files.append((item.image.storage, item.image.name))
            files.extend(
                (extra.image.storage, extra.image.name) for extra in item.extra_images.all()
            )
        super().delete_queryset(request, queryset)
        for storage, name in files:
            transaction.on_commit(
                lambda filename=name, backend=storage: self._delete_image(backend, filename)
            )


@admin.register(Favorite)
class FavoriteAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "listing", "created_at")
    search_fields = ("user__username", "listing__title")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "listing")
    list_select_related = ("user", "listing")


@admin.register(Conversation)
class ConversationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "listing", "buyer", "seller", "updated_at")
    search_fields = ("listing__title", "buyer__username", "seller__username")
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("listing", "buyer", "seller")
    list_select_related = ("listing", "buyer", "seller")


@admin.register(Message)
class MessageAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("conversation", "sender", "short_body", "created_at")
    search_fields = ("body", "sender__username")
    readonly_fields = ("created_at",)
    raw_id_fields = ("conversation", "sender")
    list_select_related = ("conversation", "sender")

    @admin.display(description="메시지")
    def short_body(self, obj):
        return obj.body[:60]


@admin.register(ListingImage)
class ListingImageAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "listing", "position", "created_at")
    search_fields = ("listing__title",)
    raw_id_fields = ("listing",)
    list_select_related = ("listing",)


@admin.register(ListingDefect)
class ListingDefectAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("listing", "code", "created_at")
    list_filter = ("code",)
    search_fields = ("listing__title",)
    raw_id_fields = ("listing",)
    list_select_related = ("listing",)


@admin.register(SavedSearch)
class SavedSearchAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("user", "query", "category", "region", "created_at")
    search_fields = ("user__username", "query", "region")
    raw_id_fields = ("user",)
    list_select_related = ("user",)


@admin.register(ListingEvent)
class ListingEventAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "listing", "kind", "old_price", "new_price", "processed_at")
    list_filter = ("kind", "processed_at")
    raw_id_fields = ("listing",)
    list_select_related = ("listing",)


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("recipient", "event", "read_at", "created_at")
    search_fields = ("recipient__username", "event__listing__title")
    raw_id_fields = ("recipient", "event", "saved_search")
    list_select_related = ("recipient", "event", "saved_search")


@admin.register(Trade)
class TradeAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "listing", "conversation", "status", "completed_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = (
        "listing__title",
        "conversation__buyer__username",
        "conversation__seller__username",
    )
    raw_id_fields = ("listing", "conversation")
    list_select_related = ("listing", "conversation")


@admin.register(Review)
class ReviewAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("trade", "direction", "rating", "visibility", "created_at")
    list_filter = ("direction", "rating", "visibility", "created_at")
    search_fields = ("body",)
    raw_id_fields = ("trade",)
    list_select_related = ("trade",)


class ReportImageEvidenceAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    # Evidence is deliberately not registered as a standalone admin model.
    # Reviewers must enter through ReportAdmin so view_report is rechecked and
    # internal storage names are never rendered in an index or change form.
    list_display = ("report", "position")
    raw_id_fields = ("report",)
    list_select_related = ("report",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    exclude = ("listing_image_name_snapshot", "listing_image_sha256")
    list_display = (
        "id",
        "reporter",
        "target_display",
        "category",
        "status",
        "resolver",
        "created_at",
    )
    list_filter = ("status", "category", "created_at", "resolved_at")
    search_fields = (
        "details",
        "reporter__username",
        "target_user__username",
        "listing__title",
    )
    readonly_fields = (
        "reporter",
        "target_user",
        "listing",
        "category",
        "details",
        "listing_title_snapshot",
        "listing_description_snapshot",
        "listing_price_snapshot",
        "listing_category_snapshot",
        "listing_condition_snapshot",
        "listing_region_snapshot",
        "listing_status_snapshot",
        "listing_image_name_snapshot",
        "listing_image_sha256",
        "listing_defect_disclosure_snapshot",
        "listing_defect_details_snapshot",
        "listing_defect_codes_snapshot",
        "listing_image_evidence_link",
        "listing_all_image_evidence_links",
        "status",
        "resolver",
        "created_at",
        "updated_at",
        "resolved_at",
    )
    list_select_related = ("reporter", "target_user", "listing", "resolver")
    actions = (
        "resolve_reports",
        "block_reported_listings",
        "restore_auto_blocked_listings",
        "suspend_reported_users",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        # Reports are evidence records. Direct change-form POSTs must not even
        # refresh auto_now metadata; all state changes go through audited,
        # permission-checked actions below.
        raise PermissionDenied

    def get_urls(self):
        custom_urls = [
            path(
                "<int:object_id>/evidence-image/",
                self.admin_site.admin_view(self.evidence_image_view),
                name="market_report_evidence_image",
            ),
            path(
                "<int:object_id>/evidence-images/<int:evidence_id>/",
                self.admin_site.admin_view(self.evidence_item_view),
                name="market_report_evidence_item",
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description="보존된 신고 이미지")
    def listing_image_evidence_link(self, obj):
        if not obj or not obj.listing_image_name_snapshot or not obj.listing_image_sha256:
            return "없음"
        return format_html(
            '<a href="{}">무결성 검증 후 원본 보기</a>',
            reverse("admin:market_report_evidence_image", args=[obj.pk]),
        )

    @admin.display(description="보존된 전체 상품 사진")
    def listing_all_image_evidence_links(self, obj):
        if not obj:
            return "없음"
        evidence_items = list(obj.image_evidence.order_by("position"))
        if not evidence_items:
            return "없음"
        return format_html_join(
            "<br>",
            '<a href="{}">사진 {} 무결성 검증 후 보기</a>',
            (
                (
                    reverse(
                        "admin:market_report_evidence_item",
                        args=[obj.pk, evidence.pk],
                    ),
                    evidence.position + 1,
                )
                for evidence in evidence_items
            ),
        )

    def _verified_evidence_response(self, request, report, name, expected_digest, *, position):
        if not name or not expected_digest:
            raise Http404
        storage = Listing._meta.get_field("image").storage
        try:
            with storage.open(name, "rb") as source:
                evidence = source.read(MAX_IMAGE_BYTES + 1)
        except (FileNotFoundError, OSError) as exc:
            raise Http404 from exc
        if len(evidence) > MAX_IMAGE_BYTES:
            security_logger.warning(
                "report_evidence_oversized report=%s position=%s",
                report.pk,
                position,
            )
            raise Http404
        actual_digest = hashlib.sha256(evidence).hexdigest()
        if not hmac.compare_digest(actual_digest, expected_digest):
            security_logger.warning(
                "report_evidence_integrity_failed report=%s position=%s",
                report.pk,
                position,
            )
            raise Http404
        response = FileResponse(io.BytesIO(evidence), content_type="image/jpeg")
        response.headers["Content-Disposition"] = 'inline; filename="report-evidence.jpg"'
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        security_logger.info(
            "report_evidence_viewed actor=%s report=%s position=%s",
            request.user.pk,
            report.pk,
            position,
        )
        return response

    def evidence_image_view(self, request, object_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        report = get_object_or_404(Report, pk=object_id)
        if not self.has_view_permission(request, report):
            raise PermissionDenied
        return self._verified_evidence_response(
            request,
            report,
            report.listing_image_name_snapshot,
            report.listing_image_sha256,
            position=0,
        )

    def evidence_item_view(self, request, object_id, evidence_id):
        if not self.has_view_permission(request):
            raise PermissionDenied
        report = get_object_or_404(Report, pk=object_id)
        if not self.has_view_permission(request, report):
            raise PermissionDenied
        evidence = get_object_or_404(
            ReportImageEvidence,
            pk=evidence_id,
            report=report,
        )
        return self._verified_evidence_response(
            request,
            report,
            evidence.storage_name,
            evidence.sha256,
            position=evidence.position,
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("market.block_listing"):
            actions.pop("block_reported_listings", None)
            actions.pop("restore_auto_blocked_listings", None)
        if not request.user.has_perm("accounts.suspend_user"):
            actions.pop("suspend_reported_users", None)
        return actions

    def _require_action_permissions(self, request, target_permission=None):
        # The action list is only a UI control. Enforce permissions again here
        # so a caller cannot bypass it with a forged changelist POST.
        if not self.has_change_permission(request):
            raise PermissionDenied
        if target_permission and not request.user.has_perm(target_permission):
            raise PermissionDenied

    @staticmethod
    def _is_protected_account(request, user):
        return user.pk == request.user.pk or user.is_staff or user.is_superuser

    @admin.display(description="신고 대상")
    def target_display(self, obj):
        return obj.target_user if obj.target_user_id else obj.listing

    @staticmethod
    def _mark_resolved(report, resolver, resolved_at):
        report.status = Report.Status.RESOLVED
        report.resolver = resolver
        report.resolved_at = resolved_at
        report.save(update_fields=("status", "resolver", "resolved_at", "updated_at"))

    @admin.action(description="선택한 신고를 처리 완료로 표시", permissions=["change"])
    def resolve_reports(self, request, queryset):
        self._require_action_permissions(request)
        resolved_at = timezone.now()
        count = 0
        selected_ids = tuple(queryset.values_list("pk", flat=True))
        with transaction.atomic():
            reports = Report.objects.select_for_update().filter(
                pk__in=selected_ids,
                status=Report.Status.OPEN,
            )
            for report in reports:
                self._mark_resolved(report, request.user, resolved_at)
                self.log_change(request, report, "관리자가 신고를 처리 완료로 표시했습니다.")
                count += 1
        self.message_user(request, f"신고 {count}건을 처리 완료했습니다.", messages.SUCCESS)

    @admin.action(
        description="신고된 판매글을 차단하고 신고 처리",
        permissions=["change"],
    )
    def block_reported_listings(self, request, queryset):
        self._require_action_permissions(request, "market.block_listing")
        blocked_at = timezone.now()
        count = 0
        selected_ids = tuple(queryset.values_list("pk", flat=True))
        with transaction.atomic():
            reports = (
                Report.objects.select_for_update()
                .filter(
                    pk__in=selected_ids,
                    status=Report.Status.OPEN,
                    listing__isnull=False,
                )
                .select_related("listing")
            )
            for report in reports:
                listing = report.listing
                listing.status = Listing.Status.BLOCKED
                listing.blocked_by = request.user
                listing.blocked_reason = report.details
                listing.blocked_at = blocked_at
                listing.save(
                    update_fields=(
                        "status",
                        "blocked_by",
                        "blocked_reason",
                        "blocked_at",
                        "updated_at",
                    )
                )
                self._mark_resolved(report, request.user, blocked_at)
                self.log_change(
                    request,
                    listing,
                    f"신고 #{report.pk}에 따라 판매글을 차단했습니다.",
                )
                self.log_change(request, report, "판매글 차단 후 신고를 처리했습니다.")
                count += 1
        self.message_user(request, f"판매글 {count}건을 차단했습니다.", messages.SUCCESS)

    @admin.action(
        description="자동 신고 임계치로 차단된 판매글을 복구하고 신고를 기각",
        permissions=["change"],
    )
    def restore_auto_blocked_listings(self, request, queryset):
        self._require_action_permissions(request, "market.block_listing")
        restored_at = timezone.now()
        selected_listing_ids = tuple(
            queryset.filter(listing__isnull=False).values_list("listing_id", flat=True).distinct()
        )
        count = 0
        with transaction.atomic():
            listings = Listing.objects.select_for_update().filter(
                pk__in=selected_listing_ids,
                status=Listing.Status.BLOCKED,
                blocked_by__isnull=True,
                blocked_reason=AUTOMATIC_LISTING_BLOCK_REASON,
            )
            for listing in listings:
                pending_trade = (
                    Trade.objects.select_for_update()
                    .filter(listing=listing, status=Trade.Status.PENDING_BUYER)
                    .first()
                )
                has_completed_trade = Trade.objects.filter(
                    listing=listing,
                    status=Trade.Status.COMPLETED,
                ).exists()
                if has_completed_trade:
                    listing.status = Listing.Status.SOLD
                elif pending_trade:
                    listing.status = Listing.Status.RESERVED
                else:
                    listing.status = Listing.Status.ACTIVE
                listing.blocked_by = None
                listing.blocked_reason = ""
                listing.blocked_at = None
                listing.save(
                    update_fields=(
                        "status",
                        "blocked_by",
                        "blocked_reason",
                        "blocked_at",
                        "updated_at",
                    )
                )
                dismissed_count = 0
                reports = Report.objects.select_for_update().filter(
                    listing=listing,
                    status=Report.Status.OPEN,
                )
                for report in reports:
                    report.status = Report.Status.DISMISSED
                    report.resolver = request.user
                    report.resolved_at = restored_at
                    report.save(update_fields=("status", "resolver", "resolved_at", "updated_at"))
                    self.log_change(
                        request,
                        report,
                        "자동 차단 복구 검토에 따라 신고를 기각했습니다.",
                    )
                    dismissed_count += 1
                self.log_change(request, listing, "자동 신고 임계치 차단을 복구했습니다.")
                security_logger.warning(
                    "automatic_listing_restored actor=%s listing=%s dismissed_reports=%s",
                    request.user.pk,
                    listing.pk,
                    dismissed_count,
                )
                count += 1
        self.message_user(request, f"자동 차단 판매글 {count}건을 복구했습니다.", messages.SUCCESS)

    @admin.action(
        description="신고된 사용자를 정지하고 신고 처리",
        permissions=["change"],
    )
    def suspend_reported_users(self, request, queryset):
        self._require_action_permissions(request, "accounts.suspend_user")
        suspended_at = timezone.now()
        count = 0
        selected_ids = tuple(queryset.values_list("pk", flat=True))
        with transaction.atomic():
            reports = (
                Report.objects.select_for_update()
                .filter(
                    pk__in=selected_ids,
                    status=Report.Status.OPEN,
                    target_user__isnull=False,
                )
                .select_related("target_user")
            )
            for report in reports:
                user = report.target_user
                if self._is_protected_account(request, user):
                    # Leave the report open for deliberate review by a more
                    # privileged administrator; never bulk-suspend admins.
                    continue
                user.is_active = False
                user.is_suspended = True
                user.suspension_reason = report.details[:500]
                user.suspended_at = suspended_at
                user.save(
                    update_fields=(
                        "is_active",
                        "is_suspended",
                        "suspension_reason",
                        "suspended_at",
                    )
                )
                self._mark_resolved(report, request.user, suspended_at)
                self.log_change(
                    request,
                    user,
                    f"신고 #{report.pk}에 따라 사용자 계정을 정지했습니다.",
                )
                self.log_change(request, report, "사용자 정지 후 신고를 처리했습니다.")
                count += 1
        self.message_user(request, f"사용자 {count}명을 정지했습니다.", messages.SUCCESS)


@admin.register(WalletAccount)
class WalletAccountAdmin(ImmutableLedgerAdminMixin, admin.ModelAdmin):
    list_display = ("id", "owner", "kind", "balance_cache", "updated_at")
    list_filter = ("kind",)
    search_fields = ("owner__username",)
    list_select_related = ("owner",)


@admin.register(Transfer)
class TransferAdmin(ImmutableLedgerAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "sender_account",
        "receiver_account",
        "amount",
        "initiated_by",
        "created_at",
    )
    list_filter = ("kind", "created_at")
    search_fields = ("id", "idempotency_key", "initiated_by__username")
    list_select_related = ("sender_account", "receiver_account", "initiated_by")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ImmutableLedgerAdminMixin, admin.ModelAdmin):
    list_display = ("id", "transfer", "account", "delta", "created_at")
    list_filter = ("created_at",)
    search_fields = ("transfer__id", "account__owner__username")
    list_select_related = ("transfer", "account", "account__owner")
