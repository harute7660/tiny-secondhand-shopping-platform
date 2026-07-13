import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.html import escape

from accounts.models import UserBlock

from .models import Favorite, Listing, ListingEvent, Notification, SavedSearch
from .services import create_listing_event, dispatch_listing_event


class SavedSearchNotificationSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.seller = user_model.objects.create_user(username="alert-seller")
        cls.subscriber = user_model.objects.create_user(username="alert-subscriber")
        cls.intruder = user_model.objects.create_user(username="alert-intruder")
        cls.blocked = user_model.objects.create_user(username="alert-blocked")
        cls.suspended = user_model.objects.create_user(username="alert-suspended")
        cls.eligible = user_model.objects.create_user(username="alert-eligible")
        cls.listing = Listing.objects.create(
            seller=cls.seller,
            title="안전한 중고 노트북",
            description="정상 작동하는 업무용 노트북입니다.",
            price_points=30_000,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            region="서울 마포구",
        )

    def setUp(self):
        cache.clear()

    @staticmethod
    def _listing_payload(*, title, price, region="서울 마포구"):
        return {
            "title": title,
            "description": "구성품과 상태를 확인한 안전한 중고 상품입니다.",
            "price_points": price,
            "category": Listing.Category.ELECTRONICS,
            "condition": Listing.Condition.GOOD,
            "region": region,
            "defect_disclosure": Listing.DefectDisclosure.UNKNOWN,
            "defect_details": "",
        }

    @staticmethod
    def _update_payload(listing, *, price):
        return {
            "title": listing.title,
            "description": listing.description,
            "price_points": price,
            "category": listing.category,
            "condition": listing.condition,
            "region": listing.region,
            "defect_disclosure": listing.defect_disclosure,
            "defect_details": listing.defect_details,
        }

    def test_state_changing_routes_require_login_post_and_csrf(self):
        create_url = reverse("market:saved_search_create")
        delete_url = reverse("market:saved_search_delete", args=[uuid.uuid4()])
        read_url = reverse("market:notification_read", args=[uuid.uuid4()])
        read_all_url = reverse("market:notification_read_all")

        for url in (create_url, delete_url, read_url, read_all_url):
            with self.subTest(url=url, method="post-anonymous"):
                self.assertEqual(self.client.post(url).status_code, 302)

        self.client.force_login(self.subscriber)
        for url in (create_url, delete_url, read_url, read_all_url):
            with self.subTest(url=url, method="get-authenticated"):
                self.assertEqual(self.client.get(url).status_code, 405)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.subscriber)
        self.assertEqual(
            csrf_client.post(
                create_url,
                {"query": "노트북", "category": "", "region": ""},
            ).status_code,
            403,
        )

    def test_normalized_duplicate_saved_search_is_stored_once(self):
        self.client.force_login(self.subscriber)
        url = reverse("market:saved_search_create")

        first = self.client.post(
            url,
            {"query": "  ＡＢＣ   상품  ", "category": "", "region": ""},
        )
        second = self.client.post(
            url,
            {"query": "abc 상품", "category": "", "region": ""},
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        searches = SavedSearch.objects.filter(user=self.subscriber)
        self.assertEqual(searches.count(), 1)
        self.assertEqual(searches.get().query, "ABC 상품")

    def test_saved_search_quota_stops_the_twenty_first_condition(self):
        for index in range(20):
            SavedSearch.objects.create(
                user=self.subscriber,
                query=f"관심 조건 {index:02d}",
            )
        self.client.force_login(self.subscriber)

        response = self.client.post(
            reverse("market:saved_search_create"),
            {"query": "스물한 번째", "category": "", "region": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "최대 20개")
        self.assertEqual(SavedSearch.objects.filter(user=self.subscriber).count(), 20)

    def test_saved_search_delete_and_notification_read_are_owner_scoped(self):
        saved_search = SavedSearch.objects.create(user=self.subscriber, query="노트북")
        event = ListingEvent.objects.create(
            listing=self.listing,
            kind=ListingEvent.Kind.PRICE_DROP,
            old_price=40_000,
            new_price=30_000,
        )
        notification = Notification.objects.create(
            recipient=self.subscriber,
            event=event,
        )
        self.client.force_login(self.intruder)

        delete_response = self.client.post(
            reverse("market:saved_search_delete", args=[saved_search.pk])
        )
        read_response = self.client.post(
            reverse("market:notification_read", args=[notification.pk])
        )
        read_all_response = self.client.post(reverse("market:notification_read_all"))

        self.assertEqual(delete_response.status_code, 404)
        self.assertEqual(read_response.status_code, 404)
        self.assertEqual(read_all_response.status_code, 302)
        self.assertTrue(SavedSearch.objects.filter(pk=saved_search.pk).exists())
        notification.refresh_from_db()
        self.assertIsNone(notification.read_at)

        self.client.force_login(self.subscriber)
        self.assertEqual(
            self.client.post(
                reverse("market:notification_read", args=[notification.pk])
            ).status_code,
            302,
        )
        notification.refresh_from_db()
        self.assertIsNotNone(notification.read_at)
        self.assertEqual(
            self.client.post(
                reverse("market:saved_search_delete", args=[saved_search.pk])
            ).status_code,
            302,
        )
        self.assertFalse(SavedSearch.objects.filter(pk=saved_search.pk).exists())

    def test_new_listing_matches_multiple_searches_but_creates_one_notification(self):
        SavedSearch.objects.create(user=self.subscriber, query="카메라")
        SavedSearch.objects.create(user=self.subscriber, region="부산")
        self.client.force_login(self.seller)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            response = self.client.post(
                reverse("market:listing_create"),
                self._listing_payload(
                    title="휴대용 중고 카메라",
                    price=45_000,
                    region="부산 해운대구",
                ),
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(callbacks), 1)
        created = Listing.objects.get(title="휴대용 중고 카메라")
        event = ListingEvent.objects.get(
            listing=created,
            kind=ListingEvent.Kind.NEW_MATCH,
        )
        self.assertIsNotNone(event.processed_at)
        notifications = Notification.objects.filter(
            recipient=self.subscriber,
            event=event,
        )
        self.assertEqual(notifications.count(), 1)

    def test_subscriptions_created_after_event_are_not_retroactive(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            event = create_listing_event(self.listing, ListingEvent.Kind.NEW_MATCH)

        self.assertEqual(len(callbacks), 1)
        late_search = SavedSearch.objects.create(user=self.subscriber, query="노트북")
        SavedSearch.objects.filter(pk=late_search.pk).update(
            created_at=event.created_at + timedelta(seconds=1)
        )
        callbacks[0]()
        self.assertFalse(
            Notification.objects.filter(recipient=self.subscriber, event=event).exists()
        )

        second_listing = Listing.objects.create(
            seller=self.seller,
            title="두 번째 노트북",
            description="가격 알림 경계 테스트 상품입니다.",
            price_points=20_000,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        with self.captureOnCommitCallbacks(execute=False) as price_callbacks:
            price_event = create_listing_event(
                second_listing,
                ListingEvent.Kind.PRICE_DROP,
                old_price=30_000,
            )
        late_favorite = Favorite.objects.create(
            user=self.subscriber,
            listing=second_listing,
        )
        Favorite.objects.filter(pk=late_favorite.pk).update(
            created_at=price_event.created_at + timedelta(seconds=1)
        )
        price_callbacks[0]()
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.subscriber,
                event=price_event,
            ).exists()
        )

    def test_listing_update_notifies_only_on_drop_with_locked_old_and_new_prices(self):
        Favorite.objects.create(user=self.subscriber, listing=self.listing)
        self.client.force_login(self.seller)
        update_url = reverse("market:listing_update", args=[self.listing.pk])

        with self.captureOnCommitCallbacks(execute=True) as increase_callbacks:
            increase_response = self.client.post(
                update_url,
                self._update_payload(self.listing, price=40_000),
            )
        self.assertEqual(increase_response.status_code, 302)
        self.assertEqual(len(increase_callbacks), 0)
        self.assertFalse(ListingEvent.objects.filter(kind=ListingEvent.Kind.PRICE_DROP).exists())
        self.assertEqual(Notification.objects.count(), 0)

        self.listing.refresh_from_db()
        with self.captureOnCommitCallbacks(execute=True) as drop_callbacks:
            drop_response = self.client.post(
                update_url,
                self._update_payload(self.listing, price=25_000),
            )

        self.assertEqual(drop_response.status_code, 302)
        self.assertEqual(len(drop_callbacks), 1)
        event = ListingEvent.objects.get(kind=ListingEvent.Kind.PRICE_DROP)
        self.assertEqual(event.old_price, 40_000)
        self.assertEqual(event.new_price, 25_000)
        self.assertIsNotNone(event.processed_at)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.subscriber,
                event=event,
            ).exists()
        )

    def test_blocked_suspended_and_seller_accounts_are_excluded(self):
        self.suspended.is_suspended = True
        self.suspended.save(update_fields=("is_suspended",))
        UserBlock.objects.create(blocker=self.seller, blocked=self.blocked)
        watched_users = (self.blocked, self.suspended, self.seller, self.eligible)
        for user in watched_users:
            SavedSearch.objects.create(user=user, query="노트북")
            Favorite.objects.create(user=user, listing=self.listing)

        self.client.force_login(self.seller)
        self.assertEqual(
            self.client.post(reverse("market:favorite_toggle", args=[self.listing.pk])).status_code,
            403,
        )

        new_event = ListingEvent.objects.create(
            listing=self.listing,
            kind=ListingEvent.Kind.NEW_MATCH,
            old_price=None,
            new_price=self.listing.price_points,
        )
        dispatch_listing_event(new_event.pk)

        self.listing.price_points = 20_000
        self.listing.save(update_fields=("price_points", "updated_at"))
        price_event = ListingEvent.objects.create(
            listing=self.listing,
            kind=ListingEvent.Kind.PRICE_DROP,
            old_price=30_000,
            new_price=20_000,
        )
        dispatch_listing_event(price_event.pk)

        for event in (new_event, price_event):
            self.assertSetEqual(
                set(event.notifications.values_list("recipient_id", flat=True)),
                {self.eligible.pk},
            )

    def test_private_listing_hides_title_prices_and_event_kind(self):
        private_title = "SECRET-NOTIFICATION-TITLE-7f"
        self.listing.title = private_title
        self.listing.status = Listing.Status.BLOCKED
        self.listing.save(update_fields=("title", "status", "updated_at"))
        event = ListingEvent.objects.create(
            listing=self.listing,
            kind=ListingEvent.Kind.PRICE_DROP,
            old_price=98_765,
            new_price=87_654,
        )
        Notification.objects.create(recipient=self.subscriber, event=event)
        self.client.force_login(self.subscriber)

        response = self.client.get(reverse("market:notification_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "현재 볼 수 없는 상품")
        self.assertContains(response, "PRIVATE")
        self.assertNotContains(response, private_title)
        self.assertNotContains(response, "98765")
        self.assertNotContains(response, "87654")
        self.assertNotContains(response, "PRICE DROP")
        self.assertNotContains(response, "NEW MATCH")

    def test_malicious_title_and_saved_query_are_escaped(self):
        payload = "<script>alert(81273)</script>"
        self.client.force_login(self.subscriber)
        self.assertEqual(
            self.client.post(
                reverse("market:saved_search_create"),
                {"query": payload, "category": "", "region": ""},
            ).status_code,
            302,
        )
        saved_search = SavedSearch.objects.get(user=self.subscriber)
        malicious_listing = Listing.objects.create(
            seller=self.seller,
            title=f"{payload} 중고 상품",
            description="이스케이프 검증용 설명입니다.",
            price_points=10_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        event = ListingEvent.objects.create(
            listing=malicious_listing,
            kind=ListingEvent.Kind.NEW_MATCH,
            old_price=None,
            new_price=malicious_listing.price_points,
        )
        dispatch_listing_event(event.pk)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.subscriber,
                event=event,
                saved_search=saved_search,
            ).exists()
        )

        response = self.client.get(reverse("market:notification_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, payload)
        self.assertContains(response, escape(payload))

    def test_dispatch_is_idempotent_even_when_pending_state_is_retried(self):
        SavedSearch.objects.create(user=self.subscriber, query="노트북")
        event = ListingEvent.objects.create(
            listing=self.listing,
            kind=ListingEvent.Kind.NEW_MATCH,
            old_price=None,
            new_price=self.listing.price_points,
        )

        self.assertEqual(dispatch_listing_event(event.pk), 1)
        self.assertEqual(dispatch_listing_event(event.pk), 1)
        ListingEvent.objects.filter(pk=event.pk).update(processed_at=None)
        self.assertEqual(dispatch_listing_event(event.pk), 1)
        self.assertEqual(Notification.objects.filter(event=event).count(), 1)

    def test_create_event_dispatches_only_from_on_commit_callback(self):
        SavedSearch.objects.create(user=self.subscriber, query="노트북")

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            event = create_listing_event(self.listing, ListingEvent.Kind.NEW_MATCH)
            self.assertEqual(Notification.objects.filter(event=event).count(), 0)

        self.assertEqual(len(callbacks), 1)
        event.refresh_from_db()
        self.assertIsNone(event.processed_at)
        callbacks[0]()
        event.refresh_from_db()
        self.assertIsNotNone(event.processed_at)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.subscriber,
                event=event,
            ).count(),
            1,
        )
