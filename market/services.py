import logging
import uuid
import warnings
from datetime import timedelta
from io import BytesIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from .evidence import EvidenceCaptureError, ensure_trade_evidence
from .models import (
    AUTOMATIC_LISTING_BLOCK_REASON,
    AUTOMATIC_REPORT_THRESHOLD,
    AUTOMATIC_USER_SUSPENSION_REASON,
    MAX_TRANSFER_POINTS,
    Conversation,
    Favorite,
    LedgerEntry,
    Listing,
    ListingEvent,
    Notification,
    Report,
    SavedSearch,
    Trade,
    Transfer,
    WalletAccount,
    normalize_saved_search_text,
)

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_BATCH_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
ALLOWED_IMAGE_MIME_TYPES = {
    "JPEG": {"image/jpeg", "image/pjpeg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
}
AUTOMATIC_LISTING_BLOCKED = "listing_blocked"
AUTOMATIC_USER_SUSPENDED = "user_suspended"
AUTOMATIC_PROTECTED_USER_SKIPPED = "protected_user_skipped"
AUTOMATIC_REPORTER_MIN_AGE = timedelta(days=7)
security_logger = logging.getLogger("tiny_market.security")


class MarketServiceError(ValidationError):
    pass


class UserUnavailableError(MarketServiceError):
    pass


class InvalidTransferError(MarketServiceError):
    pass


class InsufficientFundsError(MarketServiceError):
    pass


class IdempotencyConflictError(MarketServiceError):
    pass


class InvalidImageError(MarketServiceError):
    pass


class InvalidTradeError(MarketServiceError):
    pass


def _user_is_available(user):
    return bool(
        user
        and getattr(user, "pk", None)
        and getattr(user, "is_active", False)
        and not getattr(user, "is_suspended", False)
    )


def _get_current_available_user(user):
    if not user or not getattr(user, "pk", None):
        raise UserUnavailableError("활성 사용자가 필요합니다.")

    user_model = get_user_model()
    try:
        current_user = user_model._default_manager.get(pk=user.pk)
    except user_model.DoesNotExist as exc:
        raise UserUnavailableError("활성 사용자가 필요합니다.") from exc

    if not _user_is_available(current_user):
        raise UserUnavailableError("정지되었거나 비활성화된 사용자는 이 기능을 사용할 수 없습니다.")
    return current_user


def _validate_amount(amount):
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise InvalidTransferError("송금액은 정수 포인트여야 합니다.")
    if not 1 <= amount <= MAX_TRANSFER_POINTS:
        raise InvalidTransferError(f"송금액은 1 이상 {MAX_TRANSFER_POINTS:,} 이하이어야 합니다.")
    return amount


def _normalize_idempotency_key(value):
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise InvalidTransferError("유효한 멱등성 키가 필요합니다.") from exc


def _validate_existing_transfer(existing, sender_account, receiver_account, amount, kind):
    if (
        existing.sender_account_id != sender_account.pk
        or existing.receiver_account_id != receiver_account.pk
        or existing.amount != amount
        or existing.kind != kind
    ):
        raise IdempotencyConflictError("이미 다른 송금 요청에 사용된 멱등성 키입니다.")
    return existing


def _create_ledger_pair(transfer, sender_account, receiver_account, amount):
    # Portable CHECK constraints cannot aggregate child rows, so no supported
    # database backend can portably enforce "exactly two entries whose sum is
    # zero" on Transfer. This atomic posting service is therefore the only
    # creation boundary. Operational reconciliation must independently verify
    # entry count == 2, SUM(delta) == 0, and each wallet cache == SUM(delta).
    entries = (
        LedgerEntry(transfer=transfer, account=sender_account, delta=-amount),
        LedgerEntry(transfer=transfer, account=receiver_account, delta=amount),
    )
    if sum(entry.delta for entry in entries) != 0:
        raise RuntimeError("복식부기 원장 항목의 합계가 0이 아닙니다.")
    created_entries = LedgerEntry.objects.bulk_create(entries)
    if len(created_entries) != 2:
        raise RuntimeError("복식부기 거래에는 정확히 두 개의 원장 항목이 필요합니다.")


def ensure_wallet(user):
    """Return the single user wallet, creating it without trusting request data."""
    if not user or not getattr(user, "pk", None):
        raise UserUnavailableError("저장된 사용자만 지갑을 가질 수 있습니다.")

    wallet, _ = WalletAccount.objects.get_or_create(
        owner=user,
        defaults={"kind": WalletAccount.Kind.USER, "balance_cache": 0},
    )
    if wallet.kind != WalletAccount.Kind.USER:
        raise MarketServiceError("사용자 계정에 잘못된 지갑 종류가 연결되어 있습니다.")
    return wallet


def issue_demo_points(user, amount):
    """Issue non-cashable demo points using a balanced, immutable journal pair."""
    amount = _validate_amount(amount)

    with transaction.atomic():
        current_user = _get_current_available_user(user)
        receiver_account = ensure_wallet(current_user)
        issuance_account, _ = WalletAccount.objects.get_or_create(
            kind=WalletAccount.Kind.ISSUANCE,
            defaults={"owner": None, "balance_cache": 0},
        )

        transfer = Transfer.objects.create(
            sender_account=issuance_account,
            receiver_account=receiver_account,
            amount=amount,
            kind=Transfer.Kind.ISSUE,
            idempotency_key=uuid.uuid4(),
            initiated_by=None,
        )

        WalletAccount.objects.filter(pk=issuance_account.pk).update(
            balance_cache=F("balance_cache") - amount
        )
        credited = WalletAccount.objects.filter(
            pk=receiver_account.pk,
            kind=WalletAccount.Kind.USER,
        ).update(balance_cache=F("balance_cache") + amount)
        if credited != 1:
            raise MarketServiceError("수신 지갑에 포인트를 반영할 수 없습니다.")

        _create_ledger_pair(transfer, issuance_account, receiver_account, amount)
        return transfer


def transfer_points(sender, recipient, amount, idempotency_key):
    """
    Atomically move demo points between active users.

    SQLite does not provide effective row locks for select_for_update(), so the
    debit is one conditional UPDATE that can succeed only while funds remain.
    """
    amount = _validate_amount(amount)
    normalized_key = _normalize_idempotency_key(idempotency_key)

    sender_id = getattr(sender, "pk", None)
    recipient_id = getattr(recipient, "pk", None)

    try:
        with transaction.atomic():
            current_sender = _get_current_available_user(sender)
            current_recipient = _get_current_available_user(recipient)
            if not can_users_interact(current_sender, current_recipient):
                raise InvalidTransferError("해당 사용자에게 송금할 수 없습니다.")

            sender_account = ensure_wallet(current_sender)
            receiver_account = ensure_wallet(current_recipient)

            existing = Transfer.objects.filter(
                initiated_by=current_sender,
                idempotency_key=normalized_key,
            ).first()
            if existing:
                return _validate_existing_transfer(
                    existing,
                    sender_account,
                    receiver_account,
                    amount,
                    Transfer.Kind.USER_TRANSFER,
                )

            transfer = Transfer.objects.create(
                sender_account=sender_account,
                receiver_account=receiver_account,
                amount=amount,
                kind=Transfer.Kind.USER_TRANSFER,
                idempotency_key=normalized_key,
                initiated_by=current_sender,
            )

            debited = WalletAccount.objects.filter(
                pk=sender_account.pk,
                kind=WalletAccount.Kind.USER,
                balance_cache__gte=amount,
            ).update(balance_cache=F("balance_cache") - amount)
            if debited != 1:
                raise InsufficientFundsError("잔액이 부족합니다.")

            credited = WalletAccount.objects.filter(
                pk=receiver_account.pk,
                kind=WalletAccount.Kind.USER,
            ).update(balance_cache=F("balance_cache") + amount)
            if credited != 1:
                raise MarketServiceError("수신 지갑에 포인트를 반영할 수 없습니다.")

            _create_ledger_pair(transfer, sender_account, receiver_account, amount)
            return transfer
    except IntegrityError:
        # A concurrent replay can lose the unique-key race. Return only the
        # exact already-posted transfer; unrelated integrity errors still fail.
        existing = Transfer.objects.filter(
            initiated_by_id=sender_id,
            idempotency_key=normalized_key,
        ).first()
        if not existing:
            raise
        expected_sender = WalletAccount.objects.filter(
            owner_id=sender_id,
            kind=WalletAccount.Kind.USER,
        ).first()
        expected_receiver = WalletAccount.objects.filter(
            owner_id=recipient_id,
            kind=WalletAccount.Kind.USER,
        ).first()
        if not expected_sender or not expected_receiver:
            raise
        return _validate_existing_transfer(
            existing,
            expected_sender,
            expected_receiver,
            amount,
            Transfer.Kind.USER_TRANSFER,
        )


def can_users_interact(user_a, user_b, listing=None):
    if not _user_is_available(user_a) or not _user_is_available(user_b):
        return False
    if user_a.pk == user_b.pk:
        return False
    user_block_model = apps.get_model("accounts", "UserBlock")
    if user_block_model.objects.filter(
        Q(blocker_id=user_a.pk, blocked_id=user_b.pk)
        | Q(blocker_id=user_b.pk, blocked_id=user_a.pk)
    ).exists():
        return False
    if listing is None:
        return True
    if listing.status in {Listing.Status.BLOCKED, Listing.Status.DELETED}:
        return False
    return listing.seller_id in {user_a.pk, user_b.pk}


def _saved_search_matches_listing(saved_search, listing):
    query = normalize_saved_search_text(saved_search.query).casefold()
    region = normalize_saved_search_text(saved_search.region).casefold()
    haystack = " ".join(
        normalize_saved_search_text(value).casefold()
        for value in (listing.title, listing.description, listing.region)
    )
    return (
        (not query or query in haystack)
        and (not saved_search.category or saved_search.category == listing.category)
        and (not region or region in normalize_saved_search_text(listing.region).casefold())
    )


def dispatch_listing_event(event_id):
    """Create structured, idempotent notifications inside an atomic boundary."""
    with transaction.atomic():
        event = (
            ListingEvent.objects.select_for_update()
            .select_related("listing__seller")
            .get(pk=event_id)
        )
        if event.processed_at is not None:
            return event.notifications.count()
        listing = event.listing
        if listing.status not in {
            Listing.Status.ACTIVE,
            Listing.Status.RESERVED,
        } or not _user_is_available(listing.seller):
            event.processed_at = timezone.now()
            event.save(update_fields=("processed_at",))
            return 0

        user_block_model = apps.get_model("accounts", "UserBlock")
        blocked_pairs = user_block_model.objects.filter(
            Q(blocker_id=listing.seller_id) | Q(blocked_id=listing.seller_id)
        ).values_list("blocker_id", "blocked_id")
        blocked_user_ids = {
            blocked_id if blocker_id == listing.seller_id else blocker_id
            for blocker_id, blocked_id in blocked_pairs
        }
        recipients = {}
        if event.kind == ListingEvent.Kind.NEW_MATCH:
            searches = (
                SavedSearch.objects.filter(
                    created_at__lte=event.created_at,
                    user__is_active=True,
                    user__is_suspended=False,
                )
                .exclude(user_id=listing.seller_id)
                .exclude(user_id__in=blocked_user_ids)
                .order_by("user_id", "created_at", "pk")
            )
            for saved_search in searches.iterator(chunk_size=200):
                if saved_search.user_id in recipients:
                    continue
                if not _saved_search_matches_listing(saved_search, listing):
                    continue
                recipients[saved_search.user_id] = saved_search
        else:
            favorites = (
                Favorite.objects.filter(
                    listing=listing,
                    created_at__lte=event.created_at,
                    user__is_active=True,
                    user__is_suspended=False,
                )
                .exclude(user_id=listing.seller_id)
                .exclude(user_id__in=blocked_user_ids)
                .order_by("user_id")
            )
            for favorite in favorites.iterator(chunk_size=200):
                recipients[favorite.user_id] = None

        Notification.objects.bulk_create(
            [
                Notification(
                    recipient_id=recipient_id,
                    event=event,
                    saved_search=saved_search,
                )
                for recipient_id, saved_search in recipients.items()
            ],
            batch_size=200,
            ignore_conflicts=True,
        )
        created_count = event.notifications.count()
        event.processed_at = timezone.now()
        event.save(update_fields=("processed_at",))
        security_logger.info(
            "listing_event_dispatched event=%s notifications=%s",
            event.pk,
            created_count,
        )
        return created_count


def _dispatch_listing_event_safely(event_id):
    """Keep notification fan-out failures from rolling back a valid listing write."""
    try:
        return dispatch_listing_event(event_id)
    except Exception:
        security_logger.exception("listing_event_dispatch_failed event=%s", event_id)
        return 0


def create_listing_event(listing, kind, *, old_price=None):
    if kind == ListingEvent.Kind.NEW_MATCH:
        event = ListingEvent(
            listing=listing,
            kind=kind,
            old_price=None,
            new_price=listing.price_points,
        )
    elif kind == ListingEvent.Kind.PRICE_DROP and old_price is not None:
        event = ListingEvent(
            listing=listing,
            kind=kind,
            old_price=old_price,
            new_price=listing.price_points,
        )
    else:
        raise MarketServiceError("유효하지 않은 상품 이벤트입니다.")
    event.full_clean()
    event.save()
    # Fan-out starts only after the surrounding listing transaction commits.
    # A failed callback leaves processed_at NULL so a worker can retry it.
    transaction.on_commit(lambda event_id=event.pk: _dispatch_listing_event_safely(event_id))
    return event


def request_trade_completion(actor, conversation_id):
    """Let the seller select the buyer bound to one protected conversation."""
    current_actor = _get_current_available_user(actor)
    with transaction.atomic():
        conversation = get_user_conversation_for_trade(
            conversation_id,
            seller_id=current_actor.pk,
        )
        listing = (
            Listing.objects.select_for_update()
            .select_related("seller")
            .get(pk=conversation.listing_id)
        )
        if listing.status not in {
            Listing.Status.ACTIVE,
            Listing.Status.RESERVED,
        }:
            raise InvalidTradeError("현재 상태에서는 거래 완료를 요청할 수 없습니다.")
        if not can_users_interact(current_actor, conversation.buyer, listing):
            raise InvalidTradeError("현재 상대방과 거래를 확정할 수 없습니다.")

        existing = Trade.objects.filter(
            listing=listing,
            status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
        ).first()
        if existing:
            if (
                existing.conversation_id == conversation.pk
                and existing.status == Trade.Status.PENDING_BUYER
            ):
                try:
                    ensure_trade_evidence(existing, listing)
                except EvidenceCaptureError as exc:
                    security_logger.exception(
                        "trade_evidence_capture_failed trade=%s listing=%s",
                        existing.pk,
                        listing.pk,
                    )
                    raise InvalidTradeError(
                        "거래 증거를 안전하게 보존하지 못해 요청을 처리하지 않았습니다."
                    ) from exc
                return existing
            raise InvalidTradeError("이미 다른 거래 완료 절차가 진행 중입니다.")

        now = timezone.now()
        trade = Trade(
            listing=listing,
            conversation=conversation,
            status=Trade.Status.PENDING_BUYER,
            initial_listing_status=listing.status,
            seller_confirmed_at=now,
        )
        trade.full_clean()
        try:
            # The inner savepoint keeps the outer transaction usable when a
            # second request wins the conditional unique constraint between
            # our pre-check and INSERT (for example on a multi-worker DB).
            with transaction.atomic():
                trade.save()
        except IntegrityError:
            existing = Trade.objects.filter(
                listing=listing,
                status__in=(Trade.Status.PENDING_BUYER, Trade.Status.COMPLETED),
            ).first()
            if (
                existing is not None
                and existing.conversation_id == conversation.pk
                and existing.status == Trade.Status.PENDING_BUYER
            ):
                try:
                    ensure_trade_evidence(existing, listing)
                except EvidenceCaptureError as exc:
                    security_logger.exception(
                        "trade_evidence_capture_failed trade=%s listing=%s",
                        existing.pk,
                        listing.pk,
                    )
                    raise InvalidTradeError(
                        "거래 증거를 안전하게 보존하지 못해 요청을 처리하지 않았습니다."
                    ) from exc
                if listing.status == Listing.Status.ACTIVE:
                    listing.status = Listing.Status.RESERVED
                    listing.save(update_fields=("status", "updated_at"))
                security_logger.info(
                    "trade_completion_duplicate_reused actor=%s trade=%s",
                    current_actor.pk,
                    existing.pk,
                )
                return existing
            if existing is not None:
                raise InvalidTradeError("이미 다른 거래 완료 절차가 진행 중입니다.") from None
            raise
        try:
            ensure_trade_evidence(trade, listing)
        except EvidenceCaptureError as exc:
            security_logger.exception(
                "trade_evidence_capture_failed trade=%s listing=%s",
                trade.pk,
                listing.pk,
            )
            raise InvalidTradeError(
                "거래 증거를 안전하게 보존하지 못해 요청을 처리하지 않았습니다."
            ) from exc
        if listing.status == Listing.Status.ACTIVE:
            listing.status = Listing.Status.RESERVED
            listing.save(update_fields=("status", "updated_at"))
        security_logger.info(
            "trade_completion_requested actor=%s trade=%s",
            current_actor.pk,
            trade.pk,
        )
        return trade


def get_user_conversation_for_trade(conversation_id, *, seller_id=None, buyer_id=None):
    queryset = Conversation.objects.select_related("listing", "buyer", "seller")
    if seller_id is not None:
        queryset = queryset.filter(seller_id=seller_id)
    if buyer_id is not None:
        queryset = queryset.filter(buyer_id=buyer_id)
    try:
        return queryset.get(pk=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise InvalidTradeError("거래 대화를 찾을 수 없습니다.") from exc


def _restore_listing_after_unfinished_trade(listing, trade):
    if listing.status != Listing.Status.RESERVED:
        return
    if trade.initial_listing_status in {
        Listing.Status.ACTIVE,
        Listing.Status.RESERVED,
    }:
        listing.status = trade.initial_listing_status
        listing.save(update_fields=("status", "updated_at"))


def _can_finalize_trade(buyer, seller, listing):
    """A post-request user block cannot be used to suppress completion or reviews."""
    return bool(
        _user_is_available(buyer)
        and _user_is_available(seller)
        and listing.status not in {Listing.Status.BLOCKED, Listing.Status.DELETED}
        and listing.seller_id == seller.pk
    )


def respond_trade_completion(actor, trade_id, *, approve):
    current_actor = _get_current_available_user(actor)
    trade_ref = (
        Trade.objects.filter(pk=trade_id, conversation__buyer_id=current_actor.pk)
        .values("listing_id")
        .first()
    )
    if trade_ref is None:
        raise InvalidTradeError("거래 완료 요청을 찾을 수 없습니다.")

    with transaction.atomic():
        listing = (
            Listing.objects.select_for_update()
            .select_related("seller")
            .get(pk=trade_ref["listing_id"])
        )
        trade = (
            Trade.objects.select_for_update()
            .select_related("conversation__buyer", "conversation__seller")
            .get(pk=trade_id, conversation__buyer_id=current_actor.pk)
        )
        if trade.status != Trade.Status.PENDING_BUYER:
            raise InvalidTradeError("이미 처리된 거래 완료 요청입니다.")
        now = timezone.now()
        trade.buyer_responded_at = now
        if approve:
            if not _can_finalize_trade(
                current_actor,
                trade.conversation.seller,
                listing,
            ):
                raise InvalidTradeError("현재 거래를 완료할 수 없습니다.")
            trade.status = Trade.Status.COMPLETED
            trade.completed_at = now
            listing.status = Listing.Status.SOLD
            listing.save(update_fields=("status", "updated_at"))
            event_name = "trade_completion_confirmed"
        else:
            trade.status = Trade.Status.REJECTED
            trade.closed_at = now
            _restore_listing_after_unfinished_trade(listing, trade)
            event_name = "trade_completion_rejected"
        trade.full_clean()
        trade.save(
            update_fields=(
                "status",
                "buyer_responded_at",
                "completed_at",
                "closed_at",
                "updated_at",
            )
        )
        security_logger.info("%s actor=%s trade=%s", event_name, current_actor.pk, trade.pk)
        return trade


def cancel_trade_completion(actor, trade_id):
    current_actor = _get_current_available_user(actor)
    trade_ref = (
        Trade.objects.filter(pk=trade_id, conversation__seller_id=current_actor.pk)
        .values("listing_id")
        .first()
    )
    if trade_ref is None:
        raise InvalidTradeError("거래 완료 요청을 찾을 수 없습니다.")
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=trade_ref["listing_id"])
        trade = Trade.objects.select_for_update().get(
            pk=trade_id,
            conversation__seller_id=current_actor.pk,
        )
        if trade.status != Trade.Status.PENDING_BUYER:
            raise InvalidTradeError("이미 처리된 거래 완료 요청입니다.")
        trade.status = Trade.Status.CANCELLED
        trade.closed_at = timezone.now()
        _restore_listing_after_unfinished_trade(listing, trade)
        trade.full_clean()
        trade.save(update_fields=("status", "closed_at", "updated_at"))
        security_logger.info(
            "trade_completion_cancelled actor=%s trade=%s",
            current_actor.pk,
            trade.pk,
        )
        return trade


def apply_automatic_report_threshold(report):
    """Apply the three-eligible-reporter rule inside the caller's transaction.

    Reports from new accounts are retained for moderator review, but they do not
    immediately contribute to an automatic restriction.  This raises the cost of
    the simplest three-account Sybil attack without hiding or discarding evidence.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("신고 임계치 처리는 원자적 트랜잭션 안에서 실행해야 합니다.")
    if report.status != Report.Status.OPEN:
        return None

    now = timezone.now()
    reporter_joined_cutoff = now - AUTOMATIC_REPORTER_MIN_AGE
    if report.listing_id:
        listing = Listing.objects.select_for_update().get(pk=report.listing_id)
        distinct_reporters = (
            Report.objects.filter(
                listing_id=listing.pk,
                status=Report.Status.OPEN,
                reporter__date_joined__lte=reporter_joined_cutoff,
                reporter__is_active=True,
                reporter__is_suspended=False,
            )
            .exclude(reporter_id=listing.seller_id)
            .values("reporter_id")
            .distinct()
            .count()
        )
        if distinct_reporters < AUTOMATIC_REPORT_THRESHOLD:
            return None
        if listing.status in {Listing.Status.BLOCKED, Listing.Status.DELETED}:
            return None

        listing.status = Listing.Status.BLOCKED
        listing.blocked_by = None
        listing.blocked_reason = AUTOMATIC_LISTING_BLOCK_REASON
        listing.blocked_at = now
        listing.save(
            update_fields=(
                "status",
                "blocked_by",
                "blocked_reason",
                "blocked_at",
                "updated_at",
            )
        )
        security_logger.warning(
            "automatic_listing_blocked listing=%s trigger_report=%s distinct_reporters=%s",
            listing.pk,
            report.pk,
            distinct_reporters,
        )
        return AUTOMATIC_LISTING_BLOCKED

    user_model = get_user_model()
    target = user_model.objects.select_for_update().get(pk=report.target_user_id)
    distinct_reporters = (
        Report.objects.filter(
            target_user_id=target.pk,
            status=Report.Status.OPEN,
            reporter__date_joined__lte=reporter_joined_cutoff,
            reporter__is_active=True,
            reporter__is_suspended=False,
        )
        .exclude(reporter_id=target.pk)
        .values("reporter_id")
        .distinct()
        .count()
    )
    if distinct_reporters < AUTOMATIC_REPORT_THRESHOLD:
        return None
    if target.pk == report.reporter_id or target.is_staff or target.is_superuser:
        security_logger.warning(
            "automatic_user_suspension_skipped target=%s trigger_report=%s protected=true",
            target.pk,
            report.pk,
        )
        return AUTOMATIC_PROTECTED_USER_SKIPPED
    if target.is_suspended or not target.is_active:
        return None

    target.is_active = False
    target.is_suspended = True
    target.suspension_reason = AUTOMATIC_USER_SUSPENSION_REASON
    target.suspended_at = now
    target.save(
        update_fields=(
            "is_active",
            "is_suspended",
            "suspension_reason",
            "suspended_at",
        )
    )
    security_logger.warning(
        "automatic_user_suspended target=%s trigger_report=%s distinct_reporters=%s",
        target.pk,
        report.pk,
        distinct_reporters,
    )
    return AUTOMATIC_USER_SUSPENDED


def process_listing_image(uploaded_file):
    """Validate an uploaded raster image and return a metadata-free JPEG."""
    if uploaded_file is None:
        return None

    reported_size = getattr(uploaded_file, "size", None)
    if reported_size is not None and (reported_size <= 0 or reported_size > MAX_IMAGE_BYTES):
        raise InvalidImageError("이미지는 5MB 이하의 비어 있지 않은 파일이어야 합니다.")

    try:
        uploaded_file.seek(0)
        payload = uploaded_file.read(MAX_IMAGE_BYTES + 1)
    except (AttributeError, OSError) as exc:
        raise InvalidImageError("이미지 파일을 읽을 수 없습니다.") from exc

    if not payload or len(payload) > MAX_IMAGE_BYTES:
        raise InvalidImageError("이미지는 5MB 이하의 비어 있지 않은 파일이어야 합니다.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as probe:
                detected_format = (probe.format or "").upper()
                if detected_format not in ALLOWED_IMAGE_MIME_TYPES:
                    raise InvalidImageError("JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.")
                width, height = probe.size
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("이미지 해상도는 1,200만 픽셀 이하여야 합니다.")
                if getattr(probe, "n_frames", 1) != 1:
                    raise InvalidImageError("애니메이션 이미지는 업로드할 수 없습니다.")
                probe.verify()

        declared_type = (getattr(uploaded_file, "content_type", "") or "").split(";", 1)[0].lower()
        if declared_type and declared_type not in ALLOWED_IMAGE_MIME_TYPES[detected_format]:
            raise InvalidImageError("파일 내용과 Content-Type이 일치하지 않습니다.")

        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as source:
                if getattr(source, "n_frames", 1) != 1:
                    raise InvalidImageError("애니메이션 이미지는 업로드할 수 없습니다.")
                source.load()
                normalized = ImageOps.exif_transpose(source)

                if normalized.mode in {"RGBA", "LA"} or "transparency" in normalized.info:
                    rgba = normalized.convert("RGBA")
                    rgb = Image.new("RGB", rgba.size, "white")
                    rgb.paste(rgba, mask=rgba.getchannel("A"))
                else:
                    rgb = normalized.convert("RGB")

                encoded = None
                for quality in (85, 75, 65):
                    output = BytesIO()
                    rgb.save(output, format="JPEG", quality=quality, optimize=True)
                    if output.tell() <= MAX_IMAGE_BYTES:
                        encoded = output.getvalue()
                        break
                if encoded is None:
                    raise InvalidImageError("처리된 이미지가 5MB를 초과합니다.")
    except InvalidImageError:
        raise
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise InvalidImageError("손상되었거나 허용되지 않은 이미지입니다.") from exc

    return ContentFile(encoded, name=f"{uuid.uuid4().hex}.jpg")
