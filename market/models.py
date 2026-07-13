import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

MIN_LISTING_PRICE = 100
MAX_LISTING_PRICE = 100_000_000
MAX_TRANSFER_POINTS = 10_000_000
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


def listing_image_upload_to(instance, filename):
    """Discard the untrusted original name and always store a JPEG path."""
    return f"listings/{instance.pk}/{uuid.uuid4().hex}.jpg"


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
        REVERSAL = "REVERSAL", "반전 거래"

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
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="reversal",
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
