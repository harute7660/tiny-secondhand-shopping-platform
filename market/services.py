import uuid
import warnings
from io import BytesIO

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import MAX_TRANSFER_POINTS, LedgerEntry, Listing, Transfer, WalletAccount

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
ALLOWED_IMAGE_MIME_TYPES = {
    "JPEG": {"image/jpeg", "image/pjpeg"},
    "PNG": {"image/png"},
    "WEBP": {"image/webp"},
}


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
