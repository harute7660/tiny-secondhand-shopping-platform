import hashlib
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .evidence import EvidenceCaptureError
from .models import (
    Conversation,
    ImmutableEvidenceError,
    Listing,
    ListingDefect,
    ListingImage,
    Trade,
    TradeEvidence,
    TradeImageEvidence,
)
from .services import InvalidTradeError, request_trade_completion


class TradeEvidenceSecurityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.seller = user_model.objects.create_user(username="evidence-seller")
        self.buyer = user_model.objects.create_user(username="evidence-buyer")
        self.listing = Listing.objects.create(
            seller=self.seller,
            title="거래 시점 제목",
            description="거래 시점 설명과 구성품",
            price_points=123_400,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            region="서울시 테스트구",
            defect_disclosure=Listing.DefectDisclosure.PRESENT,
            defect_details="오른쪽 모서리의 작은 흠집",
        )
        ListingDefect.objects.create(
            listing=self.listing,
            code=ListingDefect.Code.SCRATCH_DENT,
        )
        self.conversation = Conversation.objects.create(
            listing=self.listing,
            buyer=self.buyer,
            seller=self.seller,
        )

    def test_request_captures_text_structure_and_image_digests_once(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            primary_bytes = b"trade-primary-evidence"
            extra_bytes = b"trade-extra-evidence"
            self.listing.image.save(
                "primary.jpg",
                ContentFile(primary_bytes),
                save=True,
            )
            extra = ListingImage.objects.create(
                listing=self.listing,
                image=ContentFile(extra_bytes, name="extra.jpg"),
                position=1,
            )
            self.listing.refresh_from_db()

            trade = request_trade_completion(self.seller, self.conversation.pk)

            evidence = TradeEvidence.objects.get(trade=trade)
            self.assertEqual(evidence.title_snapshot, "거래 시점 제목")
            self.assertEqual(evidence.description_snapshot, "거래 시점 설명과 구성품")
            self.assertEqual(evidence.price_points_snapshot, 123_400)
            self.assertEqual(evidence.region_snapshot, "서울시 테스트구")
            self.assertEqual(evidence.listing_status_snapshot, Listing.Status.ACTIVE)
            self.assertEqual(
                evidence.defect_codes_snapshot,
                [ListingDefect.Code.SCRATCH_DENT],
            )
            images = list(evidence.images.order_by("position"))
            self.assertEqual([item.position for item in images], [0, 1])
            self.assertEqual(images[0].storage_name, self.listing.image.name)
            self.assertEqual(images[0].sha256, hashlib.sha256(primary_bytes).hexdigest())
            self.assertEqual(images[1].storage_name, extra.image.name)
            self.assertEqual(images[1].sha256, hashlib.sha256(extra_bytes).hexdigest())

            evidence.title_snapshot = "rewritten"
            with self.assertRaises(ImmutableEvidenceError):
                evidence.save()
            with self.assertRaises(ImmutableEvidenceError):
                TradeEvidence.objects.filter(pk=evidence.pk).update(title_snapshot="rewritten")
            with self.assertRaises(ImmutableEvidenceError):
                TradeImageEvidence.objects.filter(evidence=evidence).delete()

    def test_capture_failure_rolls_back_trade_and_listing_reservation(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "unavailable.jpg",
                ContentFile(b"unavailable-evidence"),
                save=True,
            )

            with patch(
                "market.evidence.hash_storage_file",
                side_effect=EvidenceCaptureError("simulated storage failure"),
            ):
                with self.assertRaises(InvalidTradeError):
                    request_trade_completion(self.seller, self.conversation.pk)

            self.listing.refresh_from_db()
            self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
            self.assertFalse(Trade.objects.exists())
            self.assertFalse(TradeEvidence.objects.exists())
            self.assertFalse(TradeImageEvidence.objects.exists())

    def test_duplicate_request_reuses_first_snapshot_without_overwrite(self):
        first_trade = request_trade_completion(self.seller, self.conversation.pk)
        first_evidence = TradeEvidence.objects.get(trade=first_trade)

        Listing.objects.filter(pk=self.listing.pk).update(title="나중에 강제로 변경된 제목")
        second_trade = request_trade_completion(self.seller, self.conversation.pk)

        self.assertEqual(second_trade.pk, first_trade.pk)
        self.assertEqual(TradeEvidence.objects.filter(trade=first_trade).count(), 1)
        first_evidence.refresh_from_db()
        self.assertEqual(first_evidence.title_snapshot, "거래 시점 제목")

    def test_legacy_completed_trade_is_captured_before_archive(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "legacy-completed.jpg",
                ContentFile(b"legacy-completed-evidence"),
                save=True,
            )
            self.listing.status = Listing.Status.SOLD
            self.listing.save(update_fields=("status", "updated_at"))
            now = timezone.now()
            trade = Trade.objects.create(
                listing=self.listing,
                conversation=self.conversation,
                status=Trade.Status.COMPLETED,
                initial_listing_status=Listing.Status.ACTIVE,
                seller_confirmed_at=now,
                buyer_responded_at=now,
                completed_at=now,
            )
            image_name = self.listing.image.name
            storage = self.listing.image.storage
            image_url = reverse("market:listing_image", args=[self.listing.pk])
            self.assertFalse(TradeEvidence.objects.filter(trade=trade).exists())

            self.client.force_login(self.seller)
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("market:listing_delete", args=[self.listing.pk])
                )

            self.assertEqual(response.status_code, 302)
            self.assertTrue(TradeEvidence.objects.filter(trade=trade).exists())
            self.assertTrue(storage.exists(image_name))
            self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_only_authorized_admin_can_stream_digest_verified_image(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            payload = b"admin-only-trade-evidence"
            self.listing.image.save(
                "admin-evidence.jpg",
                ContentFile(payload),
                save=True,
            )
            trade = request_trade_completion(self.seller, self.conversation.pk)
            image_evidence = TradeImageEvidence.objects.get(evidence__trade=trade)
            admin_url = reverse(
                "admin:market_trade_image_evidence_verified",
                args=[image_evidence.pk],
            )

            self.assertEqual(
                self.client.get(f"/trades/{trade.pk}/evidence/").status_code,
                404,
            )
            self.assertEqual(self.client.get(admin_url).status_code, 302)

            unauthorized_staff = get_user_model().objects.create_user(
                username="evidence-unprivileged-staff",
                is_staff=True,
            )
            self.client.force_login(unauthorized_staff)
            missing_admin_url = reverse(
                "admin:market_trade_image_evidence_verified",
                args=[image_evidence.pk + 999_999],
            )
            self.assertEqual(self.client.get(admin_url).status_code, 403)
            self.assertEqual(self.client.get(missing_admin_url).status_code, 403)

            admin_user = get_user_model().objects.create_superuser(
                username="evidence-admin",
                email="admin@example.test",
                password=None,
            )
            self.client.force_login(admin_user)
            response = self.client.get(admin_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "private, no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(b"".join(response.streaming_content), payload)

            storage = self.listing.image.storage
            storage.delete(image_evidence.storage_name)
            storage.save(image_evidence.storage_name, ContentFile(b"tampered"))
            self.assertEqual(self.client.get(admin_url).status_code, 404)
