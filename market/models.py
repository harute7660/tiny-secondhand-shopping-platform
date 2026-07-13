import hashlib
import json
import re
import unicodedata
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxLengthValidator,
    MaxValueValidator,
    MinValueValidator,
    RegexValidator,
)
from django.db import models
from django.db.models import F, Q

MIN_LISTING_PRICE = 100
MAX_LISTING_PRICE = 100_000_000
MAX_TRANSFER_POINTS = 10_000_000
MAX_EXTRA_LISTING_IMAGES = 4
MAX_TOTAL_LISTING_IMAGES = 1 + MAX_EXTRA_LISTING_IMAGES
MAX_SAVED_SEARCHES = 20
MAX_REVIEW_BODY_LENGTH = 500
AUTOMATIC_REPORT_THRESHOLD = 3
AUTOMATIC_LISTING_BLOCK_REASON = (
    "[AUTO] 서로 다른 신고자 3명의 미처리 신고가 접수되어 임시 차단되었습니다."
)
AUTOMATIC_USER_SUSPENSION_REASON = (
    "[AUTO] 서로 다른 신고자 3명의 미처리 신고가 접수되어 계정이 임시 정지되었습니다."
)


class ImmutableLedgerError(ValidationError):
    """Raised when application code tries to rewrite posted financial history."""


class ImmutableLedgerQuerySet(models.QuerySet):
    """Block public bulk mutation paths while retaining create/bulk_create."""

    mutation_error = "게시된 거래 및 원장 기록은 수정하거나 삭제할 수 없습니다."

    def update(self, **kwargs):
        raise ImmutableLedgerError(self.mutation_error)

    def delete(self):
        raise ImmutableLedgerError(self.mutation_error)

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableLedgerError(self.mutation_error)

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        # Normal inserts are required by the posting service. Upsert mode can
        # rewrite an existing row, so it is an update and must remain blocked.
        if update_conflicts or update_fields:
            raise ImmutableLedgerError(self.mutation_error)
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


class ImmutableLedgerManager(models.Manager.from_queryset(ImmutableLedgerQuerySet)):
    pass


class ImmutableLedgerModel(models.Model):
    """Allow the initial INSERT only; posted rows are append-only through the ORM."""

    objects = ImmutableLedgerManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableLedgerError(
                "게시된 거래 및 원장 기록은 수정할 수 없습니다. 반전 거래를 추가하세요."
            )
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        raise ImmutableLedgerError("게시된 거래 및 원장 기록은 삭제할 수 없습니다.")


class ImmutableEvidenceError(ValidationError):
    """Raised when application code attempts to rewrite retained evidence."""


class ImmutableEvidenceQuerySet(models.QuerySet):
    mutation_error = "보존된 거래 증거는 수정하거나 삭제할 수 없습니다."

    def update(self, **kwargs):
        raise ImmutableEvidenceError(self.mutation_error)

    def delete(self):
        raise ImmutableEvidenceError(self.mutation_error)

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableEvidenceError(self.mutation_error)

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        if update_conflicts or update_fields:
            raise ImmutableEvidenceError(self.mutation_error)
        return super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )


class ImmutableEvidenceManager(models.Manager.from_queryset(ImmutableEvidenceQuerySet)):
    pass


class ImmutableEvidenceModel(models.Model):
    """Insert-only ORM base for private dispute evidence."""

    objects = ImmutableEvidenceManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableEvidenceError("보존된 거래 증거는 수정할 수 없습니다.")
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        raise ImmutableEvidenceError("보존된 거래 증거는 삭제할 수 없습니다.")


def listing_image_upload_to(instance, filename):
    """Discard the untrusted original name and always store a JPEG path."""
    return f"listings/{instance.pk}/{uuid.uuid4().hex}.jpg"


def listing_extra_image_upload_to(instance, filename):
    """Store additional sanitized JPEGs without retaining client filenames."""
    return f"listings/{instance.listing_id}/{uuid.uuid4().hex}.jpg"


def normalize_saved_search_text(value):
    normalized = unicodedata.normalize("NFKC", str(value or ""))
    return re.sub(r"\s+", " ", normalized).strip()


class Listing(models.Model):
    class Category(models.TextChoices):
        ELECTRONICS = "ELECTRONICS", "전자기기"
        FASHION = "FASHION", "패션/잡화"
        HOME = "HOME", "생활/가구"
        BOOKS = "BOOKS", "도서"
        SPORTS = "SPORTS", "스포츠/레저"
        OTHER = "OTHER", "기타"

    class Condition(models.TextChoices):
        NEW = "NEW", "미사용"
        LIKE_NEW = "LIKE_NEW", "거의 새것"
        GOOD = "GOOD", "양호"
        FAIR = "FAIR", "사용감 있음"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "판매 중"
        RESERVED = "RESERVED", "예약 중"
        SOLD = "SOLD", "판매 완료"
        BLOCKED = "BLOCKED", "차단"
        DELETED = "DELETED", "삭제"

    class DefectDisclosure(models.TextChoices):
        NONE_KNOWN = "NONE_KNOWN", "확인한 하자 없음"
        PRESENT = "PRESENT", "하자 있음"
        UNKNOWN = "UNKNOWN", "확인하지 못함"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    title = models.CharField(max_length=150)
    description = models.TextField(validators=[MaxLengthValidator(5_000)])
    price_points = models.PositiveBigIntegerField(
        validators=[
            MinValueValidator(MIN_LISTING_PRICE),
            MaxValueValidator(MAX_LISTING_PRICE),
        ]
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    condition = models.CharField(max_length=20, choices=Condition.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    region = models.CharField(max_length=100)
    image = models.ImageField(upload_to=listing_image_upload_to, blank=True)
    defect_disclosure = models.CharField(
        max_length=12,
        choices=DefectDisclosure.choices,
        default=DefectDisclosure.UNKNOWN,
    )
    defect_details = models.TextField(blank=True, validators=[MaxLengthValidator(1_000)])
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="blocked_listings",
        null=True,
        blank=True,
    )
    blocked_reason = models.TextField(blank=True, validators=[MaxLengthValidator(2_000)])
    blocked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("block_listing", "Can block reported listings"),
            ("purge_listing", "Can permanently purge listings"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    price_points__gte=MIN_LISTING_PRICE,
                    price_points__lte=MAX_LISTING_PRICE,
                ),
                name="mkt_listing_price_range",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "-created_at"), name="mkt_listing_status_idx"),
            models.Index(fields=("seller", "status"), name="mkt_listing_seller_idx"),
            models.Index(fields=("category", "status"), name="mkt_listing_cat_idx"),
        ]

    def __str__(self):
        return self.title


class ListingImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="extra_images",
    )
    image = models.ImageField(upload_to=listing_extra_image_upload_to)
    position = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("position", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "position"),
                name="mkt_listing_image_position_uq",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=1, position__lte=MAX_EXTRA_LISTING_IMAGES),
                name="mkt_image_position_range",
            ),
        ]
        indexes = [
            models.Index(fields=("listing", "position"), name="mkt_listing_image_order_idx"),
        ]

    def __str__(self):
        return f"{self.listing_id} image {self.position}"


class ListingDefect(models.Model):
    class Code(models.TextChoices):
        SCRATCH_DENT = "SCRATCH_DENT", "긁힘·찍힘"
        CRACK_DAMAGE = "CRACK_DAMAGE", "깨짐·파손"
        STAIN_DISCOLOR = "STAIN_DISCOLOR", "오염·변색"
        FUNCTION_ISSUE = "FUNCTION_ISSUE", "기능 이상"
        MISSING_PART = "MISSING_PART", "구성품 누락"
        REPAIR_HISTORY = "REPAIR_HISTORY", "수리 이력"
        ODOR_HYGIENE = "ODOR_HYGIENE", "냄새·위생 문제"
        OTHER = "OTHER", "기타"

    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="defects",
    )
    code = models.CharField(max_length=24, choices=Code.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("code",)
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "code"),
                name="mkt_listing_defect_code_uq",
            ),
        ]

    def __str__(self):
        return f"{self.listing_id}: {self.get_code_display()}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "listing"),
                name="mkt_fav_user_listing_uq",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.listing}"


class SavedSearch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_searches",
    )
    query = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=20, choices=Listing.Category.choices, blank=True)
    region = models.CharField(max_length=50, blank=True)
    fingerprint = models.CharField(max_length=64, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("user", "fingerprint"),
                name="mkt_saved_user_fp_uq",
            ),
            models.CheckConstraint(
                condition=(~Q(query="") | ~Q(category="") | ~Q(region="")),
                name="mkt_saved_search_not_empty",
            ),
        ]
        indexes = [
            models.Index(fields=("user", "-created_at"), name="mkt_saved_search_user_idx"),
        ]

    def __str__(self):
        return f"{self.user}: {self.query or self.category or self.region}"

    def save(self, *args, **kwargs):
        self.query = normalize_saved_search_text(self.query)
        self.region = normalize_saved_search_text(self.region)
        self._refresh_fingerprint()
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        self.query = normalize_saved_search_text(self.query)
        self.region = normalize_saved_search_text(self.region)
        if self.query and len(self.query) < 2:
            raise ValidationError({"query": "검색어는 2자 이상 입력해 주세요."})
        if not (self.query or self.category or self.region):
            raise ValidationError("검색어, 카테고리, 지역 중 하나 이상을 지정해 주세요.")
        self._refresh_fingerprint()

    def _refresh_fingerprint(self):
        payload = json.dumps(
            {
                "category": self.category,
                "query": self.query.casefold(),
                "region": self.region.casefold(),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        self.fingerprint = hashlib.sha256(payload).hexdigest()


class ListingEvent(models.Model):
    class Kind(models.TextChoices):
        NEW_MATCH = "NEW_MATCH", "새 관심 상품"
        PRICE_DROP = "PRICE_DROP", "가격 하락"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="events",
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    old_price = models.PositiveBigIntegerField(null=True, blank=True)
    new_price = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(kind="NEW_MATCH", old_price__isnull=True)
                    | Q(kind="PRICE_DROP", old_price__isnull=False, old_price__gt=F("new_price"))
                ),
                name="mkt_listing_event_shape",
            ),
            models.UniqueConstraint(
                fields=("listing", "kind"),
                condition=Q(kind="NEW_MATCH"),
                name="mkt_listing_event_new_match_uq",
            ),
        ]
        indexes = [
            models.Index(fields=("processed_at", "created_at"), name="mkt_event_pending_idx"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.listing_id}"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="market_notifications",
    )
    event = models.ForeignKey(
        ListingEvent,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    saved_search = models.ForeignKey(
        SavedSearch,
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("recipient", "event"),
                name="mkt_notif_recipient_event_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("recipient", "read_at", "-created_at"),
                name="mkt_notif_inbox_idx",
            ),
        ]

    def __str__(self):
        return f"{self.recipient}: {self.event.get_kind_display()}"


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="conversations",
    )
    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="buying_conversations",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="selling_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "buyer"),
                name="mkt_conv_listing_buyer_uq",
            ),
            models.CheckConstraint(
                condition=~Q(buyer=F("seller")),
                name="mkt_conv_users_differ",
            ),
        ]

    def __str__(self):
        return f"{self.listing}: {self.buyer} / {self.seller}"

    def clean(self):
        super().clean()
        if self.listing_id and self.seller_id:
            listing_seller_id = self.listing.seller_id
            if listing_seller_id != self.seller_id:
                raise ValidationError(
                    {"seller": "판매글의 판매자와 대화 판매자가 일치해야 합니다."}
                )


class Trade(models.Model):
    class Status(models.TextChoices):
        PENDING_BUYER = "PENDING_BUYER", "구매자 확인 대기"
        COMPLETED = "COMPLETED", "거래 완료"
        REJECTED = "REJECTED", "구매자 거절"
        CANCELLED = "CANCELLED", "판매자 취소"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.PROTECT, related_name="trades")
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.PROTECT,
        related_name="trades",
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    initial_listing_status = models.CharField(max_length=10, choices=Listing.Status.choices)
    seller_confirmed_at = models.DateTimeField()
    buyer_responded_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("listing",),
                condition=Q(status__in=("PENDING_BUYER", "COMPLETED")),
                name="mkt_trade_listing_active_uq",
            ),
            models.UniqueConstraint(
                fields=("conversation",),
                condition=Q(status__in=("PENDING_BUYER", "COMPLETED")),
                name="mkt_trade_conv_active_uq",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        status="PENDING_BUYER",
                        buyer_responded_at__isnull=True,
                        completed_at__isnull=True,
                        closed_at__isnull=True,
                    )
                    | Q(
                        status="COMPLETED",
                        buyer_responded_at__isnull=False,
                        completed_at__isnull=False,
                        closed_at__isnull=True,
                    )
                    | Q(
                        status="REJECTED",
                        buyer_responded_at__isnull=False,
                        completed_at__isnull=True,
                        closed_at__isnull=False,
                    )
                    | Q(
                        status="CANCELLED",
                        buyer_responded_at__isnull=True,
                        completed_at__isnull=True,
                        closed_at__isnull=False,
                    )
                ),
                name="mkt_trade_status_timestamps",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "-created_at"), name="mkt_trade_status_idx"),
        ]

    def __str__(self):
        return f"{self.listing_id}: {self.get_status_display()}"

    def clean(self):
        super().clean()
        if self.listing_id and self.conversation_id:
            if self.conversation.listing_id != self.listing_id:
                raise ValidationError("거래의 상품과 대화 상품이 일치해야 합니다.")
            if self.conversation.seller_id != self.listing.seller_id:
                raise ValidationError("거래 대화의 판매자가 상품 판매자와 일치해야 합니다.")


class TradeEvidence(ImmutableEvidenceModel):
    """Private, immutable listing snapshot captured for a trade dispute."""

    trade = models.OneToOneField(
        Trade,
        on_delete=models.PROTECT,
        related_name="evidence",
    )
    title_snapshot = models.CharField(max_length=150)
    description_snapshot = models.TextField()
    price_points_snapshot = models.PositiveBigIntegerField()
    category_snapshot = models.CharField(max_length=20)
    condition_snapshot = models.CharField(max_length=20)
    region_snapshot = models.CharField(max_length=100)
    listing_status_snapshot = models.CharField(max_length=10)
    defect_disclosure_snapshot = models.CharField(max_length=12)
    defect_details_snapshot = models.TextField(blank=True)
    defect_codes_snapshot = models.JSONField(default=list, blank=True)
    source_updated_at = models.DateTimeField()
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-captured_at",)

    def __str__(self):
        return f"trade {self.trade_id} evidence"


class TradeImageEvidence(ImmutableEvidenceModel):
    """Storage reference and digest for one image in a trade snapshot."""

    evidence = models.ForeignKey(
        TradeEvidence,
        on_delete=models.PROTECT,
        related_name="images",
    )
    storage_name = models.CharField(max_length=500)
    sha256 = models.CharField(
        max_length=64,
        validators=[RegexValidator(r"\A[0-9a-f]{64}\Z")],
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("evidence", "position"),
                name="mkt_trade_evid_image_pos_uq",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=0, position__lte=MAX_EXTRA_LISTING_IMAGES),
                name="mkt_trade_evid_image_pos_rng",
            ),
        ]
        indexes = [
            models.Index(fields=("storage_name",), name="mkt_trade_evid_name_idx"),
        ]

    def __str__(self):
        return f"trade {self.evidence.trade_id} image {self.position}"


class Review(models.Model):
    class Direction(models.TextChoices):
        BUYER_TO_SELLER = "BUYER_TO_SELLER", "구매자가 판매자에게"
        SELLER_TO_BUYER = "SELLER_TO_BUYER", "판매자가 구매자에게"

    class Visibility(models.TextChoices):
        PENDING = "PENDING", "쌍방 후기 대기"
        PUBLIC = "PUBLIC", "공개"
        HIDDEN = "HIDDEN", "관리자 숨김"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trade = models.ForeignKey(Trade, on_delete=models.PROTECT, related_name="reviews")
    direction = models.CharField(max_length=20, choices=Direction.choices)
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    body = models.TextField(validators=[MaxLengthValidator(MAX_REVIEW_BODY_LENGTH)])
    visibility = models.CharField(
        max_length=8,
        choices=Visibility.choices,
        default=Visibility.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("trade", "direction"),
                name="mkt_review_trade_direction_uq",
            ),
            models.CheckConstraint(
                condition=Q(rating__gte=1, rating__lte=5),
                name="mkt_review_rating_range",
            ),
            models.CheckConstraint(
                condition=Q(direction__in=("BUYER_TO_SELLER", "SELLER_TO_BUYER")),
                name="mkt_review_direction_valid",
            ),
            models.CheckConstraint(
                condition=Q(visibility__in=("PENDING", "PUBLIC", "HIDDEN")),
                name="mkt_review_visibility_valid",
            ),
            models.CheckConstraint(condition=~Q(body=""), name="mkt_review_body_not_empty"),
        ]

    def __str__(self):
        return f"{self.trade_id}: {self.rating}/5"

    def clean(self):
        super().clean()
        self.body = self.body.strip()
        if not self.body:
            raise ValidationError({"body": "후기 내용을 입력해 주세요."})
        if self.trade_id and self.trade.status != Trade.Status.COMPLETED:
            raise ValidationError("상호 확인이 완료된 거래에만 후기를 작성할 수 있습니다.")


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_market_messages",
    )
    body = models.TextField(max_length=1_000, validators=[MaxLengthValidator(1_000)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        indexes = [
            models.Index(fields=("conversation", "created_at"), name="mkt_message_conv_idx"),
        ]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"

    def clean(self):
        super().clean()
        if self.conversation_id and self.sender_id:
            participants = {self.conversation.buyer_id, self.conversation.seller_id}
            if self.sender_id not in participants:
                raise ValidationError({"sender": "대화 참여자만 메시지를 보낼 수 있습니다."})


class Report(models.Model):
    class Category(models.TextChoices):
        SPAM = "SPAM", "스팸"
        FRAUD = "FRAUD", "사기 의심"
        ABUSE = "ABUSE", "욕설/괴롭힘"
        PROHIBITED = "PROHIBITED", "금지 품목"
        OTHER = "OTHER", "기타"

    class Status(models.TextChoices):
        OPEN = "OPEN", "접수"
        RESOLVED = "RESOLVED", "처리 완료"
        DISMISSED = "DISMISSED", "기각"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_reports",
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_reports",
        null=True,
        blank=True,
    )
    listing = models.ForeignKey(
        Listing,
        on_delete=models.PROTECT,
        related_name="reports",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    details = models.TextField(validators=[MaxLengthValidator(2_000)])
    listing_title_snapshot = models.CharField(max_length=150, blank=True)
    listing_description_snapshot = models.TextField(blank=True)
    listing_price_snapshot = models.PositiveBigIntegerField(null=True, blank=True)
    listing_category_snapshot = models.CharField(max_length=20, blank=True)
    listing_condition_snapshot = models.CharField(max_length=20, blank=True)
    listing_region_snapshot = models.CharField(max_length=100, blank=True)
    listing_status_snapshot = models.CharField(max_length=10, blank=True)
    listing_image_name_snapshot = models.CharField(max_length=500, blank=True)
    listing_image_sha256 = models.CharField(max_length=64, blank=True)
    listing_defect_disclosure_snapshot = models.CharField(max_length=12, blank=True)
    listing_defect_details_snapshot = models.TextField(blank=True)
    listing_defect_codes_snapshot = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    resolver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="resolved_reports",
        null=True,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(target_user__isnull=False, listing__isnull=True)
                    | Q(target_user__isnull=True, listing__isnull=False)
                ),
                name="mkt_report_one_target",
            ),
            models.UniqueConstraint(
                fields=("reporter", "listing"),
                condition=Q(status="OPEN", listing__isnull=False),
                name="mkt_report_open_listing_uniq",
            ),
            models.UniqueConstraint(
                fields=("reporter", "target_user"),
                condition=Q(status="OPEN", target_user__isnull=False),
                name="mkt_report_open_user_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=("status", "-created_at"), name="mkt_report_status_idx"),
            models.Index(
                fields=("listing_image_name_snapshot",),
                name="mkt_report_image_name_idx",
            ),
        ]

    def __str__(self):
        target = self.target_user if self.target_user_id else self.listing
        return f"{self.get_category_display()}: {target}"

    def clean(self):
        super().clean()
        if bool(self.target_user_id) == bool(self.listing_id):
            raise ValidationError("신고 대상 사용자 또는 판매글 중 하나만 지정해야 합니다.")


class ReportImageEvidence(models.Model):
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="image_evidence",
    )
    storage_name = models.CharField(max_length=500)
    sha256 = models.CharField(max_length=64, blank=True)
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ("position",)
        constraints = [
            models.UniqueConstraint(
                fields=("report", "position"),
                name="mkt_report_image_position_uq",
            ),
        ]
        indexes = [
            models.Index(fields=("storage_name",), name="mkt_report_evidence_name_idx"),
        ]

    def __str__(self):
        return f"report {self.report_id} image {self.position}"


class WalletAccount(models.Model):
    class Kind(models.TextChoices):
        USER = "USER", "사용자 지갑"
        ISSUANCE = "ISSUANCE", "포인트 발행 계정"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="wallet",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.USER)
    balance_cache = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(kind="ISSUANCE") | Q(balance_cache__gte=0),
                name="mkt_wallet_user_nonnegative",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind="USER", owner__isnull=False) | Q(kind="ISSUANCE", owner__isnull=True)
                ),
                name="mkt_wallet_owner_kind",
            ),
            models.UniqueConstraint(
                fields=("kind",),
                condition=Q(kind="ISSUANCE"),
                name="mkt_wallet_one_issuance",
            ),
        ]

    def __str__(self):
        if self.kind == self.Kind.ISSUANCE:
            return "DEMO POINT 발행 계정"
        return f"{self.owner} 지갑"


class Transfer(ImmutableLedgerModel):
    class Kind(models.TextChoices):
        ISSUE = "ISSUE", "데모 포인트 발행"
        USER_TRANSFER = "USER_TRANSFER", "사용자 송금"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    receiver_account = models.ForeignKey(
        WalletAccount,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    amount = models.PositiveBigIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(MAX_TRANSFER_POINTS)]
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    idempotency_key = models.UUIDField(default=uuid.uuid4, editable=False)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_transfers",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("initiated_by", "idempotency_key"),
                name="mkt_transfer_actor_key_uq",
            ),
            models.UniqueConstraint(
                fields=("idempotency_key",),
                condition=Q(initiated_by__isnull=True),
                name="mkt_transfer_system_key_uq",
            ),
            models.CheckConstraint(
                condition=~Q(sender_account=F("receiver_account")),
                name="mkt_transfer_accounts_diff",
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=1, amount__lte=MAX_TRANSFER_POINTS),
                name="mkt_transfer_amount_range",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=("ISSUE", "USER_TRANSFER")),
                name="mkt_transfer_kind_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("sender_account", "-created_at"), name="mkt_transfer_sender_idx"),
            models.Index(fields=("receiver_account", "-created_at"), name="mkt_transfer_recv_idx"),
        ]

    def __str__(self):
        return f"{self.sender_account} -> {self.receiver_account}: {self.amount:,}P"

    def clean(self):
        super().clean()
        if self.sender_account_id == self.receiver_account_id:
            raise ValidationError("송신 계정과 수신 계정은 달라야 합니다.")
        if self.kind == self.Kind.ISSUE:
            if self.sender_account.kind != WalletAccount.Kind.ISSUANCE:
                raise ValidationError(
                    {"sender_account": "발행 거래는 발행 계정에서 시작해야 합니다."}
                )
            if self.receiver_account.kind != WalletAccount.Kind.USER:
                raise ValidationError(
                    {"receiver_account": "발행 포인트는 사용자 지갑으로만 보낼 수 있습니다."}
                )
        elif self.kind == self.Kind.USER_TRANSFER:
            if (
                self.sender_account.kind != WalletAccount.Kind.USER
                or self.receiver_account.kind != WalletAccount.Kind.USER
            ):
                raise ValidationError("사용자 송금은 사용자 지갑 사이에서만 가능합니다.")
            if self.initiated_by_id != self.sender_account.owner_id:
                raise ValidationError(
                    {"initiated_by": "송금 요청자는 송신 지갑 소유자여야 합니다."}
                )


class LedgerEntry(ImmutableLedgerModel):
    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    account = models.ForeignKey(
        WalletAccount,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    delta = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        constraints = [
            models.UniqueConstraint(
                fields=("transfer", "account"),
                name="mkt_entry_transfer_account_uq",
            ),
            models.CheckConstraint(
                condition=~Q(delta=0),
                name="mkt_entry_delta_nonzero",
            ),
        ]
        indexes = [
            models.Index(fields=("account", "created_at"), name="mkt_entry_account_idx"),
        ]

    def __str__(self):
        return f"{self.account}: {self.delta:+,}P"
