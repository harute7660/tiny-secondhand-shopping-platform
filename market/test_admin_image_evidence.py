from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .models import Listing, ListingImage, Report, ReportImageEvidence
from .services import process_listing_image

# Fixed credential exists only inside an isolated test database.
PASSWORD = "Correct-Horse-Battery-99!"  # nosec B105


def make_image(name, color):
    output = BytesIO()
    Image.new("RGB", (40, 30), color).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class ReportImageEvidenceAdminSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.seller = user_model.objects.create_user(username="evidence-seller")
        cls.reporter = user_model.objects.create_user(username="evidence-reporter")
        cls.reviewer = user_model.objects.create_superuser(
            username="evidence-reviewer-admin",
            password=PASSWORD,
        )

    def test_all_report_images_use_report_scoped_verified_endpoint(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = Listing.objects.create(
                seller=self.seller,
                title="관리자 다중 증거 검증 상품",
                description="대표와 추가 사진의 신고 증거를 검증합니다.",
                price_points=10_000,
                category=Listing.Category.ELECTRONICS,
                condition=Listing.Condition.GOOD,
                region="서울",
            )
            listing.image.save(
                "primary.png",
                process_listing_image(make_image("primary.png", "#112233")),
                save=True,
            )
            ListingImage.objects.create(
                listing=listing,
                image=process_listing_image(make_image("extra.png", "#334455")),
                position=1,
            )
            self.client.force_login(self.reporter)
            self.client.post(
                f"{reverse('market:report_create')}?listing={listing.pk}",
                {"category": Report.Category.FRAUD, "details": "사진 증거 검토 요청"},
            )
            report = Report.objects.get(reporter=self.reporter, listing=listing)
            extra_evidence = report.image_evidence.get(position=1)

            self.assertNotIn(ReportImageEvidence, admin.site._registry)
            self.client.force_login(self.reviewer)
            change_page = self.client.get(reverse("admin:market_report_change", args=[report.pk]))
            item_url = reverse(
                "admin:market_report_evidence_item",
                args=[report.pk, extra_evidence.pk],
            )
            self.assertEqual(change_page.status_code, 200)
            self.assertContains(change_page, item_url)
            self.assertNotContains(change_page, extra_evidence.storage_name)

            response = self.client.get(item_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["Cache-Control"], "private, no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            response.close()
            wrong_parent_url = reverse(
                "admin:market_report_evidence_item",
                args=[report.pk + 1_000, extra_evidence.pk],
            )
            self.assertEqual(self.client.get(wrong_parent_url).status_code, 404)
