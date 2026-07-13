import uuid
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserBlock

from .models import (
    Conversation,
    Listing,
    ListingImage,
    Review,
    Trade,
    TradeEvidence,
    TradeImageEvidence,
)
from .services import request_trade_completion

# Fixed credential exists only inside an isolated test database.
PASSWORD = "Correct-Horse-Battery-99!"  # nosec B105


class TradeReviewSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.seller = user_model.objects.create_user(
            username="trade-seller",
            password=PASSWORD,
        )
        self.buyer = user_model.objects.create_user(
            username="trade-buyer",
            password=PASSWORD,
        )
        self.outsider = user_model.objects.create_user(
            username="trade-outsider",
            password=PASSWORD,
        )
        self.listing, self.conversation = self._make_market_pair(
            "primary",
            buyer=self.buyer,
        )

    def _make_market_pair(self, suffix, *, buyer, status=Listing.Status.ACTIVE):
        listing = Listing.objects.create(
            seller=self.seller,
            title=f"비공개 상품 식별자 {suffix}",
            description="거래 완료와 후기 보안 회귀 검사용 상품입니다.",
            price_points=8_765_431,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            status=status,
            region=f"비공개 지역 {suffix}",
            defect_disclosure=Listing.DefectDisclosure.NONE_KNOWN,
        )
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=buyer,
            seller=self.seller,
        )
        return listing, conversation

    def _request_trade(self, listing=None, conversation=None):
        listing = listing or self.listing
        conversation = conversation or self.conversation
        self.client.force_login(self.seller)
        response = self.client.post(
            reverse("market:trade_request_completion", args=[conversation.pk])
        )
        self.assertEqual(response.status_code, 302)
        return Trade.objects.get(
            listing=listing,
            conversation=conversation,
            status=Trade.Status.PENDING_BUYER,
        )

    def _complete_trade(self, listing=None, conversation=None):
        listing = listing or self.listing
        conversation = conversation or self.conversation
        trade = self._request_trade(listing, conversation)
        self.client.force_login(conversation.buyer)
        response = self.client.post(reverse("market:trade_confirm", args=[trade.pk]))
        self.assertEqual(response.status_code, 302)
        trade.refresh_from_db()
        listing.refresh_from_db()
        self.assertEqual(trade.status, Trade.Status.COMPLETED)
        self.assertEqual(listing.status, Listing.Status.SOLD)
        return trade

    def _post_review(self, actor, verified_trade, *, rating, body, **forged_fields):
        self.client.force_login(actor)
        return self.client.post(
            reverse("market:review_create", args=[verified_trade.pk]),
            {
                "rating": rating,
                "body": body,
                **forged_fields,
            },
        )

    def test_seller_request_then_buyer_confirmation_completes_bound_trade(self):
        trade = self._request_trade()
        self.listing.refresh_from_db()

        self.assertEqual(trade.conversation, self.conversation)
        self.assertEqual(trade.initial_listing_status, Listing.Status.ACTIVE)
        self.assertEqual(self.listing.status, Listing.Status.RESERVED)
        self.assertIsNone(trade.buyer_responded_at)

        self.client.force_login(self.buyer)
        response = self.client.post(reverse("market:trade_confirm", args=[trade.pk]))

        self.assertEqual(response.status_code, 302)
        trade.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(trade.status, Trade.Status.COMPLETED)
        self.assertIsNotNone(trade.buyer_responded_at)
        self.assertIsNotNone(trade.completed_at)
        self.assertEqual(self.listing.status, Listing.Status.SOLD)

    def test_reject_and_seller_cancel_restore_initial_listing_status(self):
        rejected_trade = self._request_trade()
        self.client.force_login(self.buyer)

        rejected = self.client.post(reverse("market:trade_reject", args=[rejected_trade.pk]))

        self.assertEqual(rejected.status_code, 302)
        rejected_trade.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(rejected_trade.status, Trade.Status.REJECTED)
        self.assertIsNotNone(rejected_trade.closed_at)
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
        self.client.force_login(self.seller)
        rejected_page = self.client.get(
            reverse("market:conversation_detail", args=[self.conversation.pk])
        )
        self.assertContains(rejected_page, "이전 완료 요청을 거절했습니다")

        reserved_listing, reserved_conversation = self._make_market_pair(
            "reserved",
            buyer=self.buyer,
            status=Listing.Status.RESERVED,
        )
        cancelled_trade = self._request_trade(reserved_listing, reserved_conversation)
        self.client.force_login(self.seller)

        cancelled = self.client.post(reverse("market:trade_cancel", args=[cancelled_trade.pk]))

        self.assertEqual(cancelled.status_code, 302)
        cancelled_trade.refresh_from_db()
        reserved_listing.refresh_from_db()
        self.assertEqual(cancelled_trade.status, Trade.Status.CANCELLED)
        self.assertIsNotNone(cancelled_trade.closed_at)
        self.assertEqual(reserved_listing.status, Listing.Status.RESERVED)
        cancelled_page = self.client.get(
            reverse("market:conversation_detail", args=[reserved_conversation.pk])
        )
        self.assertContains(cancelled_page, "이전 완료 요청을 취소했습니다")

    def test_other_buyer_conversation_hides_invalid_trade_call_to_action(self):
        second_buyer = get_user_model().objects.create_user(
            username="trade-second-buyer",
            password=PASSWORD,
        )
        second_conversation = Conversation.objects.create(
            listing=self.listing,
            buyer=second_buyer,
            seller=self.seller,
        )
        self._request_trade()
        self.client.force_login(self.seller)

        response = self.client.get(
            reverse("market:conversation_detail", args=[second_conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "다른 거래 완료 확인이 진행 중")
        self.assertNotContains(response, "이 구매자에게 거래 완료 확인 요청")
        self.assertNotContains(response, self.buyer.username)

    def test_message_and_review_errors_have_visible_summary(self):
        self.client.force_login(self.buyer)
        message_response = self.client.post(
            reverse("market:conversation_detail", args=[self.conversation.pk]),
            {"body": ""},
        )

        self.assertEqual(message_response.status_code, 200)
        self.assertContains(message_response, "저장되지 않았습니다")
        self.assertContains(message_response, "data-form-error-summary", html=False)

        trade = self._complete_trade()
        self.client.force_login(self.buyer)
        review_response = self.client.post(
            reverse("market:review_create", args=[trade.pk]),
            {"rating": "", "body": ""},
        )

        self.assertEqual(review_response.status_code, 400)
        self.assertContains(review_response, "저장되지 않았습니다", status_code=400)
        self.assertContains(
            review_response,
            "data-form-error-summary",
            status_code=400,
            html=False,
        )

    def test_third_party_cannot_enumerate_or_mutate_trade_and_review(self):
        self.client.force_login(self.outsider)
        request_url = reverse(
            "market:trade_request_completion",
            args=[self.conversation.pk],
        )
        self.assertEqual(self.client.post(request_url).status_code, 404)
        self.assertFalse(Trade.objects.exists())

        trade = self._request_trade()
        self.client.force_login(self.outsider)
        for route_name in ("market:trade_confirm", "market:trade_reject", "market:trade_cancel"):
            with self.subTest(route=route_name):
                self.assertEqual(
                    self.client.post(reverse(route_name, args=[trade.pk])).status_code,
                    404,
                )

        self.client.force_login(self.buyer)
        self.assertEqual(
            self.client.post(reverse("market:trade_confirm", args=[trade.pk])).status_code,
            302,
        )
        self.client.force_login(self.outsider)
        review_url = reverse("market:review_create", args=[trade.pk])
        self.assertEqual(self.client.get(review_url).status_code, 404)
        self.assertEqual(
            self.client.post(review_url, {"rating": 5, "body": "위조 후기"}).status_code,
            404,
        )
        self.assertFalse(Review.objects.exists())

    def test_legacy_sold_listing_without_verified_trade_cannot_gain_review(self):
        self.listing.status = Listing.Status.SOLD
        self.listing.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("market:trade_request_completion", args=[self.conversation.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Trade.objects.exists())
        self.client.force_login(self.buyer)
        conversation_page = self.client.get(
            reverse("market:conversation_detail", args=[self.conversation.pk])
        )
        self.assertNotContains(conversation_page, "상대방 후기 작성")
        unavailable_review = reverse("market:review_create", args=[uuid.uuid4()])
        self.assertEqual(self.client.get(unavailable_review).status_code, 404)
        self.assertFalse(Review.objects.exists())

    def test_completed_trade_blocks_update_reopen_and_new_contact(self):
        trade = self._complete_trade()
        original_title = self.listing.title
        self.client.force_login(self.seller)

        self.assertEqual(
            self.client.post(
                reverse("market:listing_status_update", args=[self.listing.pk]),
                {"status": Listing.Status.ACTIVE},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                {"title": "완료 후 위조 수정"},
            ).status_code,
            404,
        )

        # Defense in depth: even if an external/admin bug makes the listing ACTIVE,
        # the completed Trade must still prevent editing and reopening paths.
        Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.ACTIVE)
        self.assertEqual(
            self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                {"title": "완료 후 위조 수정"},
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("market:listing_status_update", args=[self.listing.pk]),
                {"status": Listing.Status.RESERVED},
            ).status_code,
            403,
        )
        self.client.force_login(self.outsider)
        self.assertEqual(
            self.client.post(
                reverse("market:conversation_start", args=[self.listing.pk])
            ).status_code,
            403,
        )

        self.listing.refresh_from_db()
        trade.refresh_from_db()
        self.assertEqual(self.listing.title, original_title)
        self.assertEqual(trade.status, Trade.Status.COMPLETED)
        self.assertFalse(
            Conversation.objects.filter(listing=self.listing, buyer=self.outsider).exists()
        )

    def test_sold_detail_never_offers_a_conversation_start_action(self):
        self._complete_trade()
        detail_url = reverse("market:listing_detail", args=[self.listing.pk])
        contact_url = reverse("market:conversation_start", args=[self.listing.pk])

        self.client.logout()
        anonymous = self.client.get(detail_url)
        self.assertEqual(anonymous.status_code, 200)
        self.assertContains(anonymous, "판매 완료된 상품이에요")
        self.assertNotContains(anonymous, contact_url)
        self.assertNotContains(anonymous, "로그인하고 거래 대화 시작")

        self.client.force_login(self.outsider)
        authenticated = self.client.get(detail_url)
        self.assertEqual(authenticated.status_code, 200)
        self.assertContains(authenticated, "판매 완료된 상품이에요")
        self.assertNotContains(authenticated, contact_url)

    def test_pending_trade_prevents_listing_archive(self):
        trade = self._request_trade()
        self.client.force_login(self.seller)
        archive_url = reverse("market:listing_delete", args=[self.listing.pk])

        self.assertEqual(self.client.get(archive_url).status_code, 403)
        self.assertEqual(self.client.post(archive_url).status_code, 403)
        self.listing.refresh_from_db()
        trade.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.RESERVED)
        self.assertEqual(trade.status, Trade.Status.PENDING_BUYER)

    def test_completed_listing_can_be_archived_without_losing_trade_or_reviews(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "completed-primary.jpg",
                ContentFile(b"private-primary-image"),
                save=True,
            )
            extra = ListingImage.objects.create(
                listing=self.listing,
                image=ContentFile(b"private-extra-image", name="completed-extra.jpg"),
                position=1,
            )
            self.listing.refresh_from_db()
            primary_url = reverse("market:listing_image", args=[self.listing.pk])
            extra_url = reverse(
                "market:listing_extra_image",
                args=[self.listing.pk, extra.pk],
            )
            primary_name = self.listing.image.name
            extra_name = extra.image.name
            storage = self.listing.image.storage

            trade = self._complete_trade()
            self._post_review(
                self.buyer,
                trade,
                rating=5,
                body="설명과 같은 상품이었습니다.",
            )
            self._post_review(
                self.seller,
                trade,
                rating=5,
                body="약속을 잘 지킨 구매자였습니다.",
            )
            self.assertEqual(Review.objects.filter(trade=trade).count(), 2)

            self.client.force_login(self.seller)
            archive_url = reverse("market:listing_delete", args=[self.listing.pk])
            confirmation = self.client.get(archive_url)
            self.assertEqual(confirmation.status_code, 200)
            self.assertContains(confirmation, "완료 상품을 목록에서 숨길까요?")
            self.assertContains(confirmation, "거래·후기 기록은 보존됩니다")
            with self.captureOnCommitCallbacks(execute=True):
                archived = self.client.post(archive_url)

            self.assertEqual(archived.status_code, 302)
            self.listing.refresh_from_db()
            trade.refresh_from_db()
            self.assertEqual(self.listing.status, Listing.Status.DELETED)
            self.assertEqual(self.listing.title, "숨김 처리된 상품")
            self.assertEqual(self.listing.description, "")
            self.assertEqual(self.listing.region, "")
            self.assertEqual(self.listing.defect_details, "")
            self.assertFalse(self.listing.image)
            self.assertFalse(ListingImage.objects.filter(listing=self.listing).exists())
            # Public listing references are removed, while private immutable
            # evidence keeps the underlying files for an authorized dispute.
            self.assertTrue(storage.exists(primary_name))
            self.assertTrue(storage.exists(extra_name))
            self.assertEqual(trade.status, Trade.Status.COMPLETED)
            self.assertEqual(Review.objects.filter(trade=trade).count(), 2)
            evidence = TradeEvidence.objects.get(trade=trade)
            self.assertEqual(evidence.title_snapshot, "비공개 상품 식별자 primary")
            self.assertEqual(evidence.price_points_snapshot, 8_765_431)
            self.assertEqual(evidence.listing_status_snapshot, Listing.Status.ACTIVE)
            self.assertEqual(
                list(evidence.images.values_list("position", "storage_name")),
                [(0, primary_name), (1, extra_name)],
            )
            self.assertTrue(
                all(
                    len(digest) == 64
                    for digest in TradeImageEvidence.objects.filter(evidence=evidence).values_list(
                        "sha256", flat=True
                    )
                )
            )
            self.assertEqual(self.client.get(primary_url).status_code, 404)
            self.assertEqual(self.client.get(extra_url).status_code, 404)

            self.client.logout()
            self.assertEqual(self.client.get(primary_url).status_code, 404)
            self.assertEqual(self.client.get(extra_url).status_code, 404)

    def test_duplicate_completion_insert_race_reuses_same_pending_trade(self):
        now = timezone.now()
        existing = Trade.objects.create(
            listing=self.listing,
            conversation=self.conversation,
            status=Trade.Status.PENDING_BUYER,
            initial_listing_status=Listing.Status.ACTIVE,
            seller_confirmed_at=now,
        )
        original_filter = Trade.objects.filter
        active_lookup_count = 0

        def simulate_stale_precheck(*args, **kwargs):
            nonlocal active_lookup_count
            queryset = original_filter(*args, **kwargs)
            if kwargs.get("listing") == self.listing and kwargs.get("status__in") == (
                Trade.Status.PENDING_BUYER,
                Trade.Status.COMPLETED,
            ):
                active_lookup_count += 1
                if active_lookup_count == 1:
                    return queryset.none()
            return queryset

        with (
            patch.object(Trade.objects, "filter", side_effect=simulate_stale_precheck),
            patch.object(Trade, "full_clean", autospec=True),
            patch.object(Trade, "save", side_effect=IntegrityError("simulated race")),
        ):
            result = request_trade_completion(self.seller, self.conversation.pk)

        self.listing.refresh_from_db()
        self.assertEqual(result.pk, existing.pk)
        self.assertEqual(Trade.objects.filter(listing=self.listing).count(), 1)
        self.assertEqual(self.listing.status, Listing.Status.RESERVED)

    def test_seller_block_after_request_cannot_suppress_buyer_confirmation(self):
        trade = self._request_trade()
        UserBlock.objects.create(blocker=self.seller, blocked=self.buyer)
        self.client.force_login(self.buyer)

        response = self.client.post(reverse("market:trade_confirm", args=[trade.pk]))

        self.assertEqual(response.status_code, 302)
        trade.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(trade.status, Trade.Status.COMPLETED)
        self.assertEqual(self.listing.status, Listing.Status.SOLD)

    def test_reviews_are_server_direction_bound_blind_published_and_unique(self):
        trade = self._complete_trade()
        buyer_body = "설명과 동일한 상태의 물건을 받았습니다."
        first = self._post_review(
            self.buyer,
            trade,
            rating=5,
            body=buyer_body,
            direction=Review.Direction.SELLER_TO_BUYER,
            visibility=Review.Visibility.PUBLIC,
            trade=str(uuid.uuid4()),
        )

        self.assertEqual(first.status_code, 302)
        buyer_review = Review.objects.get(trade=trade)
        self.assertEqual(buyer_review.direction, Review.Direction.BUYER_TO_SELLER)
        self.assertEqual(buyer_review.visibility, Review.Visibility.PENDING)
        seller_profile = self.client.get(
            reverse("accounts:public_profile", args=[self.seller.username])
        )
        self.assertNotContains(seller_profile, buyer_body)
        self.assertEqual(seller_profile.context["review_count"], 0)
        listing_detail = self.client.get(reverse("market:listing_detail", args=[self.listing.pk]))
        self.assertIsNone(listing_detail.context["seller_average_rating"])
        self.assertNotContains(listing_detail, "평균 5.0점")

        seller_body = "약속 시간을 잘 지킨 구매자였습니다."
        second = self._post_review(
            self.seller,
            trade,
            rating=4,
            body=seller_body,
            direction=Review.Direction.BUYER_TO_SELLER,
            visibility=Review.Visibility.PUBLIC,
        )

        self.assertEqual(second.status_code, 302)
        self.assertEqual(Review.objects.filter(trade=trade).count(), 2)
        buyer_review.refresh_from_db()
        seller_review = Review.objects.get(
            trade=trade,
            direction=Review.Direction.SELLER_TO_BUYER,
        )
        self.assertEqual(buyer_review.visibility, Review.Visibility.PUBLIC)
        self.assertEqual(seller_review.visibility, Review.Visibility.PUBLIC)

        duplicate = self._post_review(
            self.buyer,
            trade,
            rating=1,
            body="중복으로 덮어쓰려는 후기입니다.",
        )
        self.assertEqual(duplicate.status_code, 302)
        self.assertEqual(Review.objects.filter(trade=trade).count(), 2)
        buyer_review.refresh_from_db()
        self.assertEqual(buyer_review.rating, 5)
        self.assertEqual(buyer_review.body, buyer_body)

    def test_review_rejects_common_public_pii_patterns(self):
        trade = self._complete_trade()
        private_bodies = (
            "연락처는 010-1234-5678입니다.",
            "다른 연락처는 010/1234/5678입니다.",
            "이메일은 reviewer@example.com 입니다.",
            "자세한 내용은 https://example.com 에 있습니다.",
            "계좌번호는 1234567890123 입니다.",
        )

        for body in private_bodies:
            with self.subTest(body=body):
                response = self._post_review(self.buyer, trade, rating=5, body=body)
                self.assertContains(response, "개인정보", status_code=400)
                self.assertFalse(Review.objects.filter(trade=trade).exists())

    def test_public_profile_escapes_xss_and_hides_trade_metadata(self):
        trade = self._complete_trade()
        xss_body = "<script>alert(1)</script>"
        self.assertEqual(
            self._post_review(self.buyer, trade, rating=5, body=xss_body).status_code,
            302,
        )
        self.assertEqual(
            self._post_review(
                self.seller,
                trade,
                rating=5,
                body="안전하고 원활한 거래였습니다.",
            ).status_code,
            302,
        )

        profile = self.client.get(reverse("accounts:public_profile", args=[self.seller.username]))

        self.assertEqual(profile.status_code, 200)
        self.assertNotContains(profile, xss_body, html=False)
        self.assertContains(profile, "&lt;script&gt;alert(1)&lt;/script&gt;", html=False)
        self.assertNotContains(profile, self.listing.title)
        self.assertNotContains(profile, str(self.listing.price_points))
        self.assertNotContains(profile, self.listing.region)
        self.assertNotContains(profile, str(trade.pk))
