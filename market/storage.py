import logging

from .models import Report

security_logger = logging.getLogger("tiny_market.security")


def delete_listing_image_unless_evidence(storage, name: str) -> bool:
    """Delete an unreferenced image, retaining private report evidence.

    Returns True only when a storage deletion was attempted successfully.
    Evidence files have no public route and require an audited retention/purge
    procedure before they may be removed.
    """
    if not name:
        return False
    if Report.objects.filter(listing_image_name_snapshot=name).exists():
        security_logger.info("report_evidence_image_retained name=%s", name)
        return False
    try:
        storage.delete(name)
    except OSError:
        security_logger.exception("listing_image_cleanup_failed")
        return False
    return True
