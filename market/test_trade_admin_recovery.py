from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory, TestCase
from django.utils import timezone

from .admin import ReportAdmin
from .models import (
    AUTOMATIC_LISTING_BLOCK_REASON,
    Conversation,
    Listing,
    Report,
    Trade,
)


class CompletedTradeAdminRecoveryTests(TestCase):
    def test_auto_moderation_restore_keeps_verified_trade_sold(self):
        user_model = get_user_model()
        seller = user_model.objects.create_user(username="recovery-seller")
        buyer = user_model.objects.create_user(username="recovery-buyer")
        reviewer = user_model.objects.create_superuser(username="recovery-admin")
        listing = Listing.objects.create(
            seller=seller,
            title="완료 거래 자동 차단 복구 상품",
            description="완료 거래가 자동 차단 복구 뒤 재판매되지 않아야 합니다.",
            price_points=12_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
            status=Listing.Status.BLOCKED,
            blocked_reason=AUTOMATIC_LISTING_BLOCK_REASON,
            blocked_at=timezone.now(),
        )
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=buyer,
            seller=seller,
        )
        now = timezone.now()
        Trade.objects.create(
            listing=listing,
            conversation=conversation,
            status=Trade.Status.COMPLETED,
            initial_listing_status=Listing.Status.ACTIVE,
            seller_confirmed_at=now,
            buyer_responded_at=now,
            completed_at=now,
        )
        report = Report.objects.create(
            reporter=buyer,
            listing=listing,
            category=Report.Category.OTHER,
            details="자동 차단 복구 검증",
        )
        request = RequestFactory().post("/admin/market/report/")
        request.user = reviewer
        request.session = {}
        request._messages = FallbackStorage(request)

        ReportAdmin(Report, admin.site).restore_auto_blocked_listings(
            request,
            Report.objects.filter(pk=report.pk),
        )

        listing.refresh_from_db()
        self.assertEqual(listing.status, Listing.Status.SOLD)
        self.assertIsNone(listing.blocked_by)
        self.assertEqual(listing.blocked_reason, "")
