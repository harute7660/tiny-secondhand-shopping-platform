import logging

from django.core.management.base import BaseCommand, CommandError

from market.models import ListingEvent
from market.services import dispatch_listing_event

logger = logging.getLogger("tiny_market.security")


class Command(BaseCommand):
    help = "Retry pending saved-search and price-drop notification events."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum pending events to process (1-1000, default: 200).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if not 1 <= limit <= 1_000:
            raise CommandError("--limit must be between 1 and 1000.")

        event_ids = list(
            ListingEvent.objects.filter(processed_at__isnull=True)
            .order_by("created_at", "pk")
            .values_list("pk", flat=True)[:limit]
        )
        processed = 0
        failed = 0
        for event_id in event_ids:
            try:
                dispatch_listing_event(event_id)
            except Exception:
                failed += 1
                logger.exception("listing_event_retry_failed event=%s", event_id)
            else:
                processed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"listing events processed={processed} failed={failed} selected={len(event_ids)}"
            )
        )
