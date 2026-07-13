import hashlib

from django.db import transaction

from .models import Listing, Trade, TradeEvidence, TradeImageEvidence


class EvidenceCaptureError(Exception):
    """Raised when a referenced listing image cannot be preserved reliably."""


def hash_storage_file(storage, name: str) -> str:
    """Return a SHA-256 digest without trusting or exposing the storage path."""
    digest = hashlib.sha256()
    try:
        with storage.open(name, "rb") as source:
            for chunk in iter(lambda: source.read(64 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise EvidenceCaptureError("거래 증거 이미지를 읽을 수 없습니다.") from exc
    return digest.hexdigest()


def ensure_trade_evidence(trade: Trade, listing: Listing) -> TradeEvidence:
    """Create one immutable snapshot while the caller holds the listing lock.

    The caller must run inside an atomic transaction and lock ``listing`` with
    ``select_for_update()``.  Repeated calls reuse the existing snapshot so a
    retried completion request cannot overwrite the first captured state.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RuntimeError("거래 증거 캡처는 원자적 트랜잭션 안에서 실행해야 합니다.")

    existing = TradeEvidence.objects.filter(trade_id=trade.pk).first()
    if existing is not None:
        return existing

    image_sources = []
    if listing.image:
        image_sources.append((0, listing.image.storage, listing.image.name))
    image_sources.extend(
        (extra.position, extra.image.storage, extra.image.name)
        for extra in listing.extra_images.order_by("position")
    )
    image_digests = [
        (position, name, hash_storage_file(storage, name))
        for position, storage, name in image_sources
    ]

    evidence = TradeEvidence(
        trade=trade,
        title_snapshot=listing.title,
        description_snapshot=listing.description,
        price_points_snapshot=listing.price_points,
        category_snapshot=listing.category,
        condition_snapshot=listing.condition,
        region_snapshot=listing.region,
        # ``initial_listing_status`` remains authoritative for a legacy row
        # repaired after the request already moved the listing to RESERVED/SOLD.
        listing_status_snapshot=trade.initial_listing_status,
        defect_disclosure_snapshot=listing.defect_disclosure,
        defect_details_snapshot=listing.defect_details,
        defect_codes_snapshot=list(listing.defects.order_by("code").values_list("code", flat=True)),
        source_updated_at=listing.updated_at,
    )
    evidence.full_clean()
    evidence.save()

    images = [
        TradeImageEvidence(
            evidence=evidence,
            storage_name=name,
            sha256=digest,
            position=position,
        )
        for position, name, digest in image_digests
    ]
    for image in images:
        image.full_clean()
    if images:
        TradeImageEvidence.objects.bulk_create(images)
    return evidence
