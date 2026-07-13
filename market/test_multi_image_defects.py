import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from .forms import ListingForm
from .models import Listing, ListingDefect, ListingImage, Report, ReportImageEvidence
from .services import MAX_IMAGE_BATCH_BYTES, process_listing_image


def make_image(name="sample.png", color="#315C45"):
    output = BytesIO()
    Image.new("RGB", (48, 36), color).save(output, format="PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class MultiImageDefectSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.alice = user_model.objects.create_user(username="multi-alice")
        cls.bob = user_model.objects.create_user(username="multi-bob")

    def setUp(self):
        cache.clear()

    @staticmethod
    def listing_data(**overrides):
        data = {
            "title": "다중 사진 보안 테스트 상품",
            "description": "사진과 하자 정보가 안전하게 처리되는지 확인합니다.",
            "price_points": 25_000,
            "category": Listing.Category.ELECTRONICS,
            "condition": Listing.Condition.GOOD,
            "region": "서울 마포구",
            "defect_disclosure": Listing.DefectDisclosure.NONE_KNOWN,
            "defect_details": "",
        }
        data.update(overrides)
        return data

    def create_listing(self, **overrides):
        values = {
            "seller": self.alice,
            "title": "보안 테스트 상품",
            "description": "다중 이미지와 하자 정보를 검증합니다.",
            "price_points": 30_000,
            "category": Listing.Category.ELECTRONICS,
            "condition": Listing.Condition.GOOD,
            "region": "서울 마포구",
        }
        values.update(overrides)
        return Listing.objects.create(**values)

    @staticmethod
    def attach_primary(listing, name="primary.png", color="#315C45"):
        listing.image.save(name, process_listing_image(make_image(name, color)), save=True)
        listing.refresh_from_db()
        return listing.image.name

    @staticmethod
    def attach_extra(listing, position, name, color="#748C7A"):
        return ListingImage.objects.create(
            listing=listing,
            image=process_listing_image(make_image(name, color)),
            position=position,
        )

    def test_primary_plus_four_extra_images_are_accepted(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.client.force_login(self.alice)
            data = self.listing_data(
                image=make_image("representative.png"),
                extra_images=[
                    make_image(f"extra-{index}.png", f"#{index + 2:02x}5544") for index in range(4)
                ],
            )

            response = self.client.post(reverse("market:listing_create"), data)

            self.assertEqual(response.status_code, 302)
            listing = Listing.objects.get(title=data["title"])
            extras = list(listing.extra_images.order_by("position"))
            self.assertTrue(listing.image)
            self.assertEqual([item.position for item in extras], [1, 2, 3, 4])
            self.assertEqual(1 + len(extras), 5)
            for stored_name in [listing.image.name, *[item.image.name for item in extras]]:
                self.assertTrue(stored_name.startswith(f"listings/{listing.pk}/"))
                self.assertTrue(stored_name.endswith(".jpg"))
                self.assertNotIn("representative.png", stored_name)
                self.assertNotIn("extra-", stored_name)

    def test_six_files_are_rejected_before_image_sanitizing(self):
        self.client.force_login(self.alice)
        data = self.listing_data(
            image=make_image("representative.png"),
            extra_images=[make_image(f"extra-{index}.png") for index in range(5)],
        )

        with patch("market.forms.process_listing_image") as sanitizer:
            response = self.client.post(reverse("market:listing_create"), data)

        self.assertEqual(response.status_code, 400)
        sanitizer.assert_not_called()
        self.assertFalse(Listing.objects.filter(title=data["title"]).exists())

    def test_representative_is_included_in_batch_limit_before_sanitizing(self):
        self.assertEqual(MAX_IMAGE_BATCH_BYTES, 20 * 1024 * 1024)
        self.client.force_login(self.alice)
        primary = make_image("representative.png")
        extra = make_image("extra.png")
        combined_size = primary.size + extra.size
        data = self.listing_data(image=primary, extra_images=[extra])

        with (
            patch("market.views.MAX_IMAGE_BATCH_BYTES", combined_size - 1),
            patch("market.forms.process_listing_image") as sanitizer,
        ):
            response = self.client.post(reverse("market:listing_create"), data)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "이미지 파일 합계", status_code=400)
        sanitizer.assert_not_called()

    def test_unexpected_file_field_is_rejected_before_sanitizing(self):
        self.client.force_login(self.alice)
        data = self.listing_data(unauthorized_upload=make_image("unexpected.png"))

        with patch("market.forms.process_listing_image") as sanitizer:
            response = self.client.post(reverse("market:listing_create"), data)

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "허용되지 않은 파일 입력", status_code=400)
        sanitizer.assert_not_called()

    def test_extra_image_route_enforces_parent_visibility_and_no_store(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = self.create_listing()
            self.attach_primary(listing)
            extra = self.attach_extra(listing, 1, "extra.png")
            other_listing = self.create_listing(title="다른 상품")
            correct_url = reverse(
                "market:listing_extra_image",
                args=[listing.pk, extra.pk],
            )
            forged_parent_url = reverse(
                "market:listing_extra_image",
                args=[other_listing.pk, extra.pk],
            )

            public_response = self.client.get(correct_url)
            self.assertEqual(public_response.status_code, 200)
            self.assertEqual(public_response.headers["Cache-Control"], "private, no-store")
            self.assertEqual(public_response.headers["X-Content-Type-Options"], "nosniff")
            public_response.close()
            self.assertEqual(self.client.get(forged_parent_url).status_code, 404)

            listing.status = Listing.Status.BLOCKED
            listing.save(update_fields=("status", "updated_at"))
            self.assertEqual(self.client.get(correct_url).status_code, 404)
            self.client.force_login(self.bob)
            self.assertEqual(self.client.get(correct_url).status_code, 404)
            self.client.force_login(self.alice)
            owner_response = self.client.get(correct_url)
            self.assertEqual(owner_response.status_code, 200)
            owner_response.close()

    def test_foreign_listing_extra_image_cannot_be_deleted(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = self.create_listing()
            self.attach_primary(listing, "listing-primary.png")
            own_extra = self.attach_extra(listing, 1, "listing-extra.png")
            other_listing = self.create_listing(title="다른 소유 상품")
            self.attach_primary(other_listing, "other-primary.png")
            foreign_extra = self.attach_extra(other_listing, 1, "foreign-extra.png")
            self.client.force_login(self.alice)

            response = self.client.post(
                reverse("market:listing_update", args=[listing.pk]),
                self.listing_data(
                    title=listing.title,
                    description=listing.description,
                    price_points=listing.price_points,
                    category=listing.category,
                    condition=listing.condition,
                    region=listing.region,
                    defect_disclosure=listing.defect_disclosure,
                    remove_extra_images=[str(foreign_extra.pk)],
                ),
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("remove_extra_images", response.context["form"].errors)
            self.assertTrue(ListingImage.objects.filter(pk=own_extra.pk, listing=listing).exists())
            self.assertTrue(
                ListingImage.objects.filter(pk=foreign_extra.pk, listing=other_listing).exists()
            )

    def test_clearing_primary_promotes_first_extra_and_cleans_old_file(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = self.create_listing()
            old_primary_name = self.attach_primary(listing, "old-primary.png")
            storage = listing.image.storage
            first_extra = self.attach_extra(listing, 1, "first-extra.png", "#554433")
            second_extra = self.attach_extra(listing, 2, "second-extra.png", "#776655")
            promoted_name = first_extra.image.name
            self.client.force_login(self.alice)

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("market:listing_update", args=[listing.pk]),
                    self.listing_data(
                        title=listing.title,
                        description=listing.description,
                        price_points=listing.price_points,
                        category=listing.category,
                        condition=listing.condition,
                        region=listing.region,
                        defect_disclosure=listing.defect_disclosure,
                        **{"image-clear": "on"},
                    ),
                )

            self.assertEqual(response.status_code, 302)
            listing.refresh_from_db()
            self.assertEqual(listing.image.name, promoted_name)
            self.assertFalse(ListingImage.objects.filter(pk=first_extra.pk).exists())
            self.assertTrue(ListingImage.objects.filter(pk=second_extra.pk).exists())
            self.assertTrue(storage.exists(promoted_name))
            self.assertFalse(storage.exists(old_primary_name))

    def test_defect_disclosure_code_and_other_detail_rules(self):
        present_without_code = ListingForm(
            data=self.listing_data(defect_disclosure=Listing.DefectDisclosure.PRESENT)
        )
        self.assertFalse(present_without_code.is_valid())
        self.assertIn("defects", present_without_code.errors)

        code_without_present = ListingForm(
            data=self.listing_data(
                defect_disclosure=Listing.DefectDisclosure.NONE_KNOWN,
                defects=[ListingDefect.Code.SCRATCH_DENT],
            )
        )
        self.assertFalse(code_without_present.is_valid())
        self.assertIn("defects", code_without_present.errors)

        other_without_details = ListingForm(
            data=self.listing_data(
                defect_disclosure=Listing.DefectDisclosure.PRESENT,
                defects=[ListingDefect.Code.OTHER],
            )
        )
        self.assertFalse(other_without_details.is_valid())
        self.assertIn("defect_details", other_without_details.errors)

        forged_code = ListingForm(
            data=self.listing_data(
                defect_disclosure=Listing.DefectDisclosure.PRESENT,
                defects=["NOT_ALLOWED"],
                defect_details="위조 코드",
            )
        )
        self.assertFalse(forged_code.is_valid())
        self.assertIn("defects", forged_code.errors)

        self.client.force_login(self.alice)
        valid_data = self.listing_data(
            title="하자 체크리스트 정상 상품",
            defect_disclosure=Listing.DefectDisclosure.PRESENT,
            defects=[ListingDefect.Code.SCRATCH_DENT, ListingDefect.Code.OTHER],
            defect_details="모서리 긁힘과 기타 사용 흔적이 있습니다.",
        )
        response = self.client.post(reverse("market:listing_create"), valid_data)
        self.assertEqual(response.status_code, 302)
        listing = Listing.objects.get(title=valid_data["title"])
        self.assertSetEqual(
            set(listing.defects.values_list("code", flat=True)),
            {ListingDefect.Code.SCRATCH_DENT, ListingDefect.Code.OTHER},
        )

    def test_defect_details_are_escaped_on_detail_page(self):
        payload = '<script>alert("defect")</script>\n<img src=x onerror=alert(1)>'
        listing = self.create_listing(
            title="하자 XSS 검증 상품",
            defect_disclosure=Listing.DefectDisclosure.PRESENT,
            defect_details=payload,
        )
        ListingDefect.objects.create(listing=listing, code=ListingDefect.Code.SCRATCH_DENT)

        response = self.client.get(reverse("market:listing_detail", args=[listing.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert("defect")</script>', html=False)
        self.assertNotContains(response, "<img src=x", html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)
        self.assertContains(response, "&lt;img", html=False)

    def test_report_snapshots_all_images_and_defects_then_retains_files_on_delete(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = self.create_listing(
                title="신고 증거 보존 상품",
                defect_disclosure=Listing.DefectDisclosure.PRESENT,
                defect_details="왼쪽 모서리 파손과 기능 이상이 있습니다.",
            )
            self.attach_primary(listing, "evidence-primary.png", "#112233")
            first_extra = self.attach_extra(listing, 1, "evidence-one.png", "#223344")
            second_extra = self.attach_extra(listing, 2, "evidence-two.png", "#334455")
            ListingDefect.objects.bulk_create(
                [
                    ListingDefect(listing=listing, code=ListingDefect.Code.CRACK_DAMAGE),
                    ListingDefect(listing=listing, code=ListingDefect.Code.FUNCTION_ISSUE),
                ]
            )
            listing.refresh_from_db()
            storage = listing.image.storage
            expected_files = {
                0: listing.image.name,
                1: first_extra.image.name,
                2: second_extra.image.name,
            }
            expected_hashes = {}
            for position, name in expected_files.items():
                with storage.open(name, "rb") as source:
                    expected_hashes[position] = hashlib.sha256(source.read()).hexdigest()

            self.client.force_login(self.bob)
            report_url = f"{reverse('market:report_create')}?listing={listing.pk}"
            response = self.client.post(
                report_url,
                {"category": Report.Category.FRAUD, "details": "사진과 하자 설명을 확인해 주세요."},
            )

            self.assertEqual(response.status_code, 302)
            report = Report.objects.get(reporter=self.bob, listing=listing)
            evidence = list(report.image_evidence.order_by("position"))
            self.assertEqual([item.position for item in evidence], [0, 1, 2])
            for item in evidence:
                self.assertEqual(item.storage_name, expected_files[item.position])
                self.assertEqual(item.sha256, expected_hashes[item.position])
            self.assertEqual(
                report.listing_defect_disclosure_snapshot,
                Listing.DefectDisclosure.PRESENT,
            )
            self.assertEqual(report.listing_defect_details_snapshot, listing.defect_details)
            self.assertSetEqual(
                set(report.listing_defect_codes_snapshot.split(",")),
                {ListingDefect.Code.CRACK_DAMAGE, ListingDefect.Code.FUNCTION_ISSUE},
            )

            self.client.force_login(self.alice)
            with self.captureOnCommitCallbacks(execute=True):
                delete_response = self.client.post(
                    reverse("market:listing_delete", args=[listing.pk])
                )

            self.assertEqual(delete_response.status_code, 302)
            listing.refresh_from_db()
            self.assertEqual(listing.status, Listing.Status.DELETED)
            self.assertFalse(listing.image)
            self.assertFalse(ListingImage.objects.filter(listing=listing).exists())
            self.assertEqual(ReportImageEvidence.objects.filter(report=report).count(), 3)
            for name in expected_files.values():
                self.assertTrue(storage.exists(name))

    def test_listing_pages_do_not_expose_internal_storage_names(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listing = self.create_listing(title="내부 경로 비노출 상품")
            primary_name = self.attach_primary(listing, "private-primary.png")
            extra = self.attach_extra(listing, 1, "private-extra.png")
            self.client.force_login(self.alice)

            update_response = self.client.get(reverse("market:listing_update", args=[listing.pk]))
            detail_response = self.client.get(reverse("market:listing_detail", args=[listing.pk]))

            for response in (update_response, detail_response):
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, primary_name)
                self.assertNotContains(response, extra.image.name)
                self.assertNotContains(response, settings.MEDIA_URL)

    def test_database_failure_after_file_write_cleans_all_orphans(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.client.force_login(self.alice)
            data = self.listing_data(
                title="롤백 파일 정리 상품",
                image=make_image("rollback-primary.png"),
                extra_images=[make_image("rollback-extra.png")],
            )
            original_save = ListingImage.save

            def persist_then_fail(instance, *args, **kwargs):
                original_save(instance, *args, **kwargs)
                raise RuntimeError("synthetic failure after storage and database write")

            with patch.object(ListingImage, "save", new=persist_then_fail):
                response = self.client.post(reverse("market:listing_create"), data)

            self.assertEqual(response.status_code, 500)
            self.assertFalse(Listing.objects.filter(title=data["title"]).exists())
            stored_files = [path for path in Path(media_root).rglob("*") if path.is_file()]
            self.assertEqual(stored_files, [])
