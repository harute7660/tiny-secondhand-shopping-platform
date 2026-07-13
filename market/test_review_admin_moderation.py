from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import ReviewAdmin
from .models import Conversation, Listing, Review, Trade


class ReviewAdminModerationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.seller = user_model.objects.create_user(username="review-admin-seller")
        self.buyer = user_model.objects.create_user(username="review-admin-buyer")
        self.moderator = user_model.objects.create_user(
            username="review-moderator",
            is_staff=True,
        )
        self.moderator.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="market",
                codename="change_review",
            )
        )
        self.outsider_staff = user_model.objects.create_user(
            username="review-outsider-staff",
            is_staff=True,
        )
        listing = Listing.objects.create(
            seller=self.seller,
            title="후기 관리자 검증 상품",
            description="후기 본문은 불변이고 공개 상태만 통제합니다.",
            price_points=10_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            status=Listing.Status.SOLD,
            region="서울",
        )
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=self.buyer,
            seller=self.seller,
        )
        self.trade = Trade.objects.create(
            listing=listing,
            conversation=conversation,
            status=Trade.Status.COMPLETED,
            initial_listing_status=Listing.Status.ACTIVE,
            seller_confirmed_at=timezone.now(),
            buyer_responded_at=timezone.now(),
            completed_at=timezone.now(),
        )
        self.buyer_review = Review.objects.create(
            trade=self.trade,
            direction=Review.Direction.BUYER_TO_SELLER,
            rating=5,
            body="판매자 후기 원문은 수정할 수 없습니다.",
            visibility=Review.Visibility.PUBLIC,
        )
        self.seller_review = Review.objects.create(
            trade=self.trade,
            direction=Review.Direction.SELLER_TO_BUYER,
            rating=4,
            body="구매자 후기 원문도 수정할 수 없습니다.",
            visibility=Review.Visibility.PUBLIC,
        )
        self.model_admin = ReviewAdmin(Review, admin.site)
        self.request_factory = RequestFactory()

    def _request(self, user):
        request = self.request_factory.post("/admin/market/review/")
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    def test_only_change_review_permission_can_hide_and_restore(self):
        queryset = Review.objects.filter(pk=self.buyer_review.pk)
        with self.assertRaises(PermissionDenied):
            self.model_admin.hide_selected_reviews(
                self._request(self.outsider_staff),
                queryset,
            )
        self.buyer_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.PUBLIC)

        with self.assertLogs("tiny_market.security", level="WARNING"):
            self.model_admin.hide_selected_reviews(self._request(self.moderator), queryset)
        self.buyer_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.HIDDEN)
        hidden_profile = self.client.get(
            reverse("accounts:public_profile", args=[self.seller.username])
        )
        self.assertNotContains(hidden_profile, self.buyer_review.body)

        with self.assertLogs("tiny_market.security", level="WARNING"):
            self.model_admin.restore_selected_reviews(self._request(self.moderator), queryset)
        self.buyer_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.PUBLIC)
        restored_profile = self.client.get(
            reverse("accounts:public_profile", args=[self.seller.username])
        )
        self.assertContains(restored_profile, self.buyer_review.body)

    def test_direct_admin_save_cannot_rewrite_review_body_or_rating(self):
        self.assertTrue(self.model_admin.has_change_permission(self._request(self.moderator)))
        self.assertFalse(
            self.model_admin.has_change_permission(
                self._request(self.moderator),
                self.buyer_review,
            )
        )
        original_body = self.buyer_review.body
        original_rating = self.buyer_review.rating
        self.buyer_review.body = "관리자가 위조한 후기"
        self.buyer_review.rating = 1

        with self.assertRaises(PermissionDenied):
            self.model_admin.save_model(
                self._request(self.moderator),
                self.buyer_review,
                form=None,
                change=True,
            )

        self.buyer_review.refresh_from_db()
        self.assertEqual(self.buyer_review.body, original_body)
        self.assertEqual(self.buyer_review.rating, original_rating)

    def test_restore_refuses_partial_blind_review_pair(self):
        self.seller_review.delete()
        Review.objects.filter(pk=self.buyer_review.pk).update(visibility=Review.Visibility.HIDDEN)

        self.model_admin.restore_selected_reviews(
            self._request(self.moderator),
            Review.objects.filter(pk=self.buyer_review.pk),
        )

        self.buyer_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.HIDDEN)

    def test_restore_refuses_hidden_review_when_counterpart_is_pending(self):
        Review.objects.filter(pk=self.buyer_review.pk).update(visibility=Review.Visibility.HIDDEN)
        Review.objects.filter(pk=self.seller_review.pk).update(visibility=Review.Visibility.PENDING)

        self.model_admin.restore_selected_reviews(
            self._request(self.moderator),
            Review.objects.filter(pk__in=(self.buyer_review.pk, self.seller_review.pk)),
        )

        self.buyer_review.refresh_from_db()
        self.seller_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.HIDDEN)
        self.assertEqual(self.seller_review.visibility, Review.Visibility.PENDING)

    def test_restore_requires_both_hidden_reviews_to_be_selected(self):
        Review.objects.filter(trade=self.trade).update(visibility=Review.Visibility.HIDDEN)

        self.model_admin.restore_selected_reviews(
            self._request(self.moderator),
            Review.objects.filter(pk=self.buyer_review.pk),
        )

        self.buyer_review.refresh_from_db()
        self.seller_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.HIDDEN)
        self.assertEqual(self.seller_review.visibility, Review.Visibility.HIDDEN)

        self.model_admin.restore_selected_reviews(
            self._request(self.moderator),
            Review.objects.filter(pk__in=(self.buyer_review.pk, self.seller_review.pk)),
        )

        self.buyer_review.refresh_from_db()
        self.seller_review.refresh_from_db()
        self.assertEqual(self.buyer_review.visibility, Review.Visibility.PUBLIC)
        self.assertEqual(self.seller_review.visibility, Review.Visibility.PUBLIC)
