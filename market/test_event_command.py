from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Listing, ListingEvent, Notification, SavedSearch


class ProcessListingEventsCommandTests(TestCase):
    def test_command_retries_pending_event_with_bounded_limit(self):
        user_model = get_user_model()
        seller = user_model.objects.create_user(username="command-seller")
        subscriber = user_model.objects.create_user(username="command-subscriber")
        listing = Listing.objects.create(
            seller=seller,
            title="재시도 대상 노트북",
            description="알림 이벤트 재시도 관리 명령 테스트입니다.",
            price_points=15_000,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        SavedSearch.objects.create(user=subscriber, query="노트북")
        event = ListingEvent.objects.create(
            listing=listing,
            kind=ListingEvent.Kind.NEW_MATCH,
            new_price=listing.price_points,
        )

        output = StringIO()
        call_command("process_listing_events", limit=1, stdout=output)

        event.refresh_from_db()
        self.assertIsNotNone(event.processed_at)
        self.assertTrue(Notification.objects.filter(recipient=subscriber, event=event).exists())
        self.assertIn("processed=1", output.getvalue())
        with self.assertRaises(CommandError):
            call_command("process_listing_events", limit=0)
