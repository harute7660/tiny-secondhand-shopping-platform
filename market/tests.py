import hashlib
import uuid
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.models import UserBlock

from .admin import (
    ConversationAdmin,
    FavoriteAdmin,
    ListingAdmin,
    ListingAdminForm,
    MessageAdmin,
    ReportAdmin,
)
from .forms import ListingForm
from .models import (
    AUTOMATIC_LISTING_BLOCK_REASON,
    AUTOMATIC_USER_SUSPENSION_REASON,
    Conversation,
    Favorite,
    ImmutableLedgerError,
    LedgerEntry,
    Listing,
    Message,
    Report,
    Transfer,
    WalletAccount,
)
from .services import (
    IdempotencyConflictError,
    InsufficientFundsError,
    issue_demo_points,
    transfer_points,
)

PASSWORD = "Correct-Horse-Battery-99!"


def make_image(name="sample.png", image_format="PNG", content_type="image/png"):
    output = BytesIO()
    Image.new("RGB", (40, 30), "#0E7C72").save(output, format=image_format)
    return SimpleUploadedFile(name, output.getvalue(), content_type=content_type)


def listing_update_data(listing, **overrides):
    data = {
        "title": listing.title,
        "description": listing.description,
        "price_points": listing.price_points,
        "category": listing.category,
        "condition": listing.condition,
        "region": listing.region,
    }
    data.update(overrides)
    return data


class MarketTestCase(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.alice = user_model.objects.create_user(username="alice", password=PASSWORD)
        self.bob = user_model.objects.create_user(username="bob", password=PASSWORD)
        self.eve = user_model.objects.create_user(username="eve", password=PASSWORD)
        for user in (self.alice, self.bob, self.eve):
            issue_demo_points(user, 100_000)
        self.listing = Listing.objects.create(
            seller=self.alice,
            title="안전한 중고 노트북",
            description="정상 작동하며 모서리에 작은 사용감이 있습니다.",
            price_points=30_000,
            category=Listing.Category.ELECTRONICS,
            condition=Listing.Condition.GOOD,
            region="서울 마포구",
        )


class ListingSecurityTests(MarketTestCase):
    def test_create_uses_session_seller_and_ignores_privileged_fields(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("market:listing_create"),
            {
                "title": "키보드",
                "description": "깨끗하게 사용했습니다.",
                "price_points": 10_000,
                "category": Listing.Category.ELECTRONICS,
                "condition": Listing.Condition.LIKE_NEW,
                "region": "서울 강남구",
                "seller": self.alice.pk,
                "status": Listing.Status.SOLD,
                "blocked_reason": "tampered",
            },
        )

        created = Listing.objects.exclude(pk=self.listing.pk).get()
        self.assertRedirects(response, reverse("market:listing_detail", args=[created.pk]))
        self.assertEqual(created.seller, self.bob)
        self.assertEqual(created.status, Listing.Status.ACTIVE)
        self.assertEqual(created.blocked_reason, "")

    def test_other_user_cannot_edit_or_delete_listing(self):
        self.client.force_login(self.bob)
        edit_url = reverse("market:listing_update", args=[self.listing.pk])
        delete_url = reverse("market:listing_delete", args=[self.listing.pk])

        self.assertEqual(self.client.get(edit_url).status_code, 404)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)

    def test_my_listings_requires_login_and_shows_only_owner_records(self):
        blocked = Listing.objects.create(
            seller=self.alice,
            title="소유자에게만 보이는 차단 상품",
            description="자동 또는 관리자 차단 상태도 소유자는 확인할 수 있습니다.",
            price_points=2_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
            status=Listing.Status.BLOCKED,
            blocked_reason="검토 중",
        )
        deleted = Listing.objects.create(
            seller=self.alice,
            title="삭제된 상품",
            description="내 상품 목록에서 제외합니다.",
            price_points=2_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
            status=Listing.Status.DELETED,
        )
        other = Listing.objects.create(
            seller=self.bob,
            title="다른 판매자의 비공개 상품",
            description="다른 판매자의 목록에는 접근할 수 없습니다.",
            price_points=2_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        url = reverse("market:my_listings")

        anonymous = self.client.get(url)
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("accounts:login"), anonymous.url)

        self.client.force_login(self.alice)
        response = self.client.get(url, {"seller": self.bob.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.listing.title)
        self.assertContains(response, blocked.title)
        self.assertContains(response, 'data-visibility="private"', html=False)
        self.assertContains(response, reverse("market:listing_detail", args=[blocked.pk]))
        self.assertNotContains(response, deleted.title)
        self.assertNotContains(response, other.title)
        self.assertTrue(
            all(item.seller_id == self.alice.pk for item in response.context["listings"])
        )

    def test_my_listings_ignores_forged_owner_query(self):
        own = Listing.objects.create(
            seller=self.bob,
            title="로그인 사용자 소유 상품",
            description="서버 세션으로 소유자를 결정합니다.",
            price_points=2_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        self.client.force_login(self.bob)

        response = self.client.get(
            reverse("market:my_listings"),
            {"seller": self.alice.pk, "user": self.alice.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own.title)
        self.assertNotContains(response, self.listing.title)

    def test_xss_payload_is_escaped_on_detail(self):
        self.listing.title = '<script>alert("x")</script>'
        self.listing.description = '<img src=x onerror=alert("x")>'
        self.listing.save()

        response = self.client.get(reverse("market:listing_detail", args=[self.listing.pk]))

        self.assertNotContains(response, '<script>alert("x")</script>', html=False)
        self.assertContains(response, "&lt;script&gt;", html=False)
        self.assertNotContains(response, '<img src=x onerror=alert("x")>', html=False)

    def test_listing_detail_links_to_seller_public_profile(self):
        response = self.client.get(reverse("market:listing_detail", args=[self.listing.pk]))
        profile_url = reverse("accounts:public_profile", args=[self.alice.username])

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{profile_url}"', html=False)
        self.assertContains(response, self.alice.username)

    def test_search_uses_orm_and_blocked_listing_is_hidden(self):
        Listing.objects.create(
            seller=self.alice,
            title="숨김 상품",
            description="관리자 차단",
            price_points=1_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
            status=Listing.Status.BLOCKED,
        )
        response = self.client.get(reverse("market:home"), {"q": "' OR 1=1 --"})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "숨김 상품")

    def test_invalid_and_oversized_prices_are_rejected(self):
        self.client.force_login(self.bob)
        base_data = {
            "title": "상품",
            "description": "설명",
            "category": Listing.Category.OTHER,
            "condition": Listing.Condition.GOOD,
            "region": "서울",
        }
        for invalid_price in (-1, 0, 100_000_001):
            response = self.client.post(
                reverse("market:listing_create"),
                {**base_data, "price_points": invalid_price},
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 1)

    def test_image_is_verified_reencoded_and_blocked_from_direct_access(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("market:listing_create"),
            {
                "title": "이미지 상품",
                "description": "정상 이미지",
                "price_points": 1_000,
                "category": Listing.Category.OTHER,
                "condition": Listing.Condition.GOOD,
                "region": "서울",
                "image": make_image(),
            },
        )
        created = Listing.objects.exclude(pk=self.listing.pk).get()
        self.assertEqual(response.status_code, 302)
        self.assertTrue(created.image.name.endswith(".jpg"))
        with created.image.open("rb") as stored:
            self.assertEqual(stored.read(2), b"\xff\xd8")

        image_url = reverse("market:listing_image", args=[created.pk])
        image_response = self.client.get(image_url)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.headers["Cache-Control"], "private, no-store")

        created.status = Listing.Status.BLOCKED
        created.save(update_fields=("status", "updated_at"))
        self.client.logout()
        self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_fake_image_is_rejected(self):
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("market:listing_create"),
            {
                "title": "위장 파일",
                "description": "이미지가 아닌 파일",
                "price_points": 1_000,
                "category": Listing.Category.OTHER,
                "condition": Listing.Condition.GOOD,
                "region": "서울",
                "image": SimpleUploadedFile(
                    "payload.jpg", b"<script>alert(1)</script>", content_type="image/jpeg"
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.count(), 1)

    def test_update_without_image_input_keeps_existing_image(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("existing.png", make_image("existing.png"), save=True)
            self.listing.refresh_from_db()
            original_name = self.listing.image.name
            storage = self.listing.image.storage
            self.client.force_login(self.alice)

            response = self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                listing_update_data(self.listing, title="이미지는 그대로 유지"),
            )

            self.assertEqual(response.status_code, 302)
            self.listing.refresh_from_db()
            self.assertEqual(self.listing.image.name, original_name)
            self.assertTrue(storage.exists(original_name))

    def test_update_clear_image_uses_filefield_normalization_and_removes_file(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("clear.png", make_image("clear.png"), save=True)
            self.listing.refresh_from_db()
            original_name = self.listing.image.name
            storage = self.listing.image.storage
            self.client.force_login(self.alice)

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("market:listing_update", args=[self.listing.pk]),
                    listing_update_data(self.listing, **{"image-clear": "on"}),
                )

            self.assertEqual(response.status_code, 302)
            self.listing.refresh_from_db()
            self.assertFalse(self.listing.image)
            self.assertFalse(storage.exists(original_name))

    def test_update_replaces_existing_image_and_removes_superseded_file(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("old.png", make_image("old.png"), save=True)
            self.listing.refresh_from_db()
            original_name = self.listing.image.name
            storage = self.listing.image.storage
            self.client.force_login(self.alice)

            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("market:listing_update", args=[self.listing.pk]),
                    listing_update_data(
                        self.listing,
                        image=make_image("replacement.png"),
                    ),
                )

            self.assertEqual(response.status_code, 302)
            self.listing.refresh_from_db()
            self.assertTrue(self.listing.image)
            self.assertNotEqual(self.listing.image.name, original_name)
            self.assertTrue(storage.exists(self.listing.image.name))
            self.assertFalse(storage.exists(original_name))

    def test_update_rejects_clear_and_upload_contradiction_without_changing_image(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("conflict.png", make_image("conflict.png"), save=True)
            self.listing.refresh_from_db()
            original_name = self.listing.image.name
            storage = self.listing.image.storage
            self.client.force_login(self.alice)

            response = self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                listing_update_data(
                    self.listing,
                    image=make_image("contradiction.png"),
                    **{"image-clear": "on"},
                ),
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("image", response.context["form"].errors)
            self.listing.refresh_from_db()
            self.assertEqual(self.listing.image.name, original_name)
            self.assertTrue(storage.exists(original_name))

    def test_update_rejects_invalid_image_without_changing_existing_image(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("valid.png", make_image("valid.png"), save=True)
            self.listing.refresh_from_db()
            original_name = self.listing.image.name
            storage = self.listing.image.storage
            self.client.force_login(self.alice)

            response = self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                listing_update_data(
                    self.listing,
                    image=SimpleUploadedFile(
                        "payload.jpg",
                        b"not-an-image",
                        content_type="image/jpeg",
                    ),
                ),
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn("image", response.context["form"].errors)
            self.listing.refresh_from_db()
            self.assertEqual(self.listing.image.name, original_name)
            self.assertTrue(storage.exists(original_name))

    def test_soft_delete_removes_private_image_after_commit(self):
        self.client.force_login(self.bob)
        self.client.post(
            reverse("market:listing_create"),
            {
                "title": "삭제할 이미지 상품",
                "description": "삭제 시 파일도 정리합니다.",
                "price_points": 1_000,
                "category": Listing.Category.OTHER,
                "condition": Listing.Condition.GOOD,
                "region": "서울",
                "image": make_image(),
            },
        )
        created = Listing.objects.exclude(pk=self.listing.pk).get()
        image_name = created.image.name
        storage = created.image.storage
        self.assertTrue(storage.exists(image_name))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse("market:listing_delete", args=[created.pk]))

        self.assertEqual(response.status_code, 302)
        created.refresh_from_db()
        self.assertEqual(created.status, Listing.Status.DELETED)
        self.assertFalse(created.image)
        self.assertFalse(storage.exists(image_name))

    def test_listing_creation_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.bob)
        response = csrf_client.post(reverse("market:listing_create"), {})
        self.assertEqual(response.status_code, 403)

    def test_suspended_seller_products_are_not_public(self):
        self.alice.is_suspended = True
        self.alice.save(update_fields=("is_suspended",))

        home = self.client.get(reverse("market:home"))
        detail = self.client.get(reverse("market:listing_detail", args=[self.listing.pk]))

        self.assertNotContains(home, self.listing.title)
        self.assertEqual(detail.status_code, 404)

    def test_staff_requires_listing_view_permission_for_blocked_content(self):
        staff = get_user_model().objects.create_user(
            username="limited-staff-view",
            password=PASSWORD,
            is_staff=True,
        )
        self.listing.status = Listing.Status.BLOCKED
        self.listing.save(update_fields=("status", "updated_at"))
        self.client.force_login(staff)
        url = reverse("market:listing_detail", args=[self.listing.pk])

        self.assertEqual(self.client.get(url).status_code, 404)
        staff.user_permissions.add(
            Permission.objects.get(content_type__app_label="market", codename="view_listing")
        )
        if hasattr(staff, "_perm_cache"):
            del staff._perm_cache
        self.client.force_login(staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_seller_status_transitions_are_server_validated(self):
        self.client.force_login(self.alice)
        url = reverse("market:listing_status_update", args=[self.listing.pk])

        self.assertEqual(
            self.client.post(url, {"status": Listing.Status.RESERVED}).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(url, {"status": Listing.Status.SOLD}).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(url, {"status": Listing.Status.ACTIVE}).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(url, {"status": Listing.Status.ACTIVE}).status_code,
            403,
        )
        self.client.force_login(self.bob)
        self.assertEqual(
            self.client.post(url, {"status": Listing.Status.SOLD}).status_code,
            404,
        )

    def test_stale_update_cannot_reverse_admin_block(self):
        self.client.force_login(self.alice)
        original_is_valid = ListingForm.is_valid

        def validate_then_block(form):
            valid = original_is_valid(form)
            Listing.objects.filter(pk=self.listing.pk).update(status=Listing.Status.BLOCKED)
            return valid

        with patch.object(
            ListingForm,
            "is_valid",
            autospec=True,
            side_effect=validate_then_block,
        ):
            response = self.client.post(
                reverse("market:listing_update", args=[self.listing.pk]),
                {
                    "title": "공격자가 덮어쓸 제목",
                    "description": self.listing.description,
                    "price_points": self.listing.price_points,
                    "category": self.listing.category,
                    "condition": self.listing.condition,
                    "region": self.listing.region,
                },
            )

        self.assertEqual(response.status_code, 403)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.BLOCKED)
        self.assertNotEqual(self.listing.title, "공격자가 덮어쓸 제목")

    def test_listing_quota_prevents_unbounded_creation(self):
        Listing.objects.bulk_create(
            [
                Listing(
                    seller=self.bob,
                    title=f"보관 상품 {index}",
                    description="보관 한도 검사",
                    price_points=1_000,
                    category=Listing.Category.OTHER,
                    condition=Listing.Condition.GOOD,
                    region="서울",
                )
                for index in range(50)
            ]
        )
        self.client.force_login(self.bob)
        response = self.client.post(
            reverse("market:listing_create"),
            {
                "title": "한도 초과",
                "description": "생성되면 안 됩니다.",
                "price_points": 1_000,
                "category": Listing.Category.OTHER,
                "condition": Listing.Condition.GOOD,
                "region": "서울",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Listing.objects.filter(seller=self.bob).count(), 50)

    def test_listing_creation_rate_limit_is_atomic_at_application_boundary(self):
        self.client.force_login(self.bob)
        url = reverse("market:listing_create")
        base = {
            "description": "등록 속도 제한 검사",
            "price_points": 1_000,
            "category": Listing.Category.OTHER,
            "condition": Listing.Condition.GOOD,
            "region": "서울",
        }
        for index in range(10):
            response = self.client.post(url, {**base, "title": f"속도 검사 {index}"})
            self.assertEqual(response.status_code, 302)

        response = self.client.post(url, {**base, "title": "속도 제한 초과"})

        self.assertEqual(response.status_code, 429)
        self.assertEqual(Listing.objects.filter(seller=self.bob).count(), 10)

    def test_listing_rate_limits_run_before_image_form_decoding(self):
        editable_listing = Listing.objects.create(
            seller=self.bob,
            title="수정 속도 제한 대상",
            description="구매자가 소유한 수정 가능한 상품입니다.",
            price_points=1_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="서울",
        )
        self.client.force_login(self.bob)
        data = {
            "title": "이미지 속도 제한 검사",
            "description": "폼 이미지 검증보다 속도 제한이 먼저 실행되어야 합니다.",
            "price_points": 1_000,
            "category": Listing.Category.OTHER,
            "condition": Listing.Condition.GOOD,
            "region": "서울",
        }
        urls = (
            reverse("market:listing_create"),
            reverse("market:listing_update", args=[editable_listing.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                with (
                    patch(
                        "market.views._consume_actor_limit",
                        side_effect=(True, False),
                    ) as consume_limit,
                    patch("market.views.ListingForm") as listing_form,
                    patch("market.forms.process_listing_image") as sanitizer,
                ):
                    response = self.client.post(
                        url,
                        {**data, "image": make_image("rate-limit.png")},
                    )

                self.assertEqual(response.status_code, 429)
                self.assertEqual(consume_limit.call_count, 2)
                listing_form.assert_not_called()
                sanitizer.assert_not_called()


class ListingAdminSecurityTests(MarketTestCase):
    def setUp(self):
        super().setUp()
        self.listing_admin = ListingAdmin(Listing, admin.site)
        self.administrator = get_user_model().objects.create_superuser(
            username="listing-admin",
            password=PASSWORD,
        )
        self.request = RequestFactory().post("/admin/market/listing/")
        self.request.user = self.administrator

    def _staff_user(self, username, *permissions):
        user = get_user_model().objects.create_user(
            username=username,
            password=PASSWORD,
            is_staff=True,
        )
        for app_label, codename in permissions:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        return user

    @staticmethod
    def _admin_request(user):
        request = RequestFactory().post("/admin/market/listing/")
        request.user = user
        return request

    def _listing_form_data(self, listing):
        return {
            "title": listing.title,
            "description": listing.description,
            "price_points": listing.price_points,
            "category": listing.category,
            "condition": listing.condition,
            "region": listing.region,
        }

    def test_admin_listing_form_rejects_fake_image(self):
        form = ListingAdminForm(
            data=self._listing_form_data(self.listing),
            files={
                "image": SimpleUploadedFile(
                    "payload.jpg",
                    b"<script>alert(1)</script>",
                    content_type="image/jpeg",
                )
            },
            instance=self.listing,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("image", form.errors)

    def test_stale_admin_change_cannot_resurrect_purged_listing(self):
        stale_listing = self.listing
        Listing.objects.filter(pk=stale_listing.pk).delete()

        with self.assertRaises(PermissionDenied):
            self.listing_admin.save_model(
                self.request,
                stale_listing,
                form=None,
                change=True,
            )

        self.assertFalse(Listing.objects.filter(pk=stale_listing.pk).exists())

    def test_hard_delete_requires_both_delete_and_purge_permissions(self):
        permission_sets = (
            (
                "delete-without-purge",
                (("market", "view_listing"), ("market", "delete_listing")),
            ),
            (
                "purge-without-delete",
                (("market", "view_listing"), ("market", "purge_listing")),
            ),
        )

        for username, permissions in permission_sets:
            with self.subTest(username=username):
                user = self._staff_user(username, *permissions)
                request = self._admin_request(user)
                self.assertFalse(self.listing_admin.has_delete_permission(request, self.listing))
                self.assertNotIn("delete_selected", self.listing_admin.get_actions(request))

                with self.assertRaises(PermissionDenied):
                    self.listing_admin.delete_model(request, self.listing)
                with self.assertRaises(PermissionDenied):
                    self.listing_admin.delete_queryset(
                        request,
                        Listing.objects.filter(pk=self.listing.pk),
                    )

                self.client.force_login(user)
                direct_response = self.client.post(
                    reverse("admin:market_listing_delete", args=[self.listing.pk]),
                    {"post": "yes"},
                )
                action_response = self.client.post(
                    reverse("admin:market_listing_changelist"),
                    {
                        "action": "delete_selected",
                        "_selected_action": [str(self.listing.pk)],
                        "select_across": "0",
                        "index": "0",
                    },
                )

                self.assertEqual(direct_response.status_code, 403)
                self.assertEqual(action_response.status_code, 200)
                self.assertTrue(Listing.objects.filter(pk=self.listing.pk).exists())

        authorized = self._staff_user(
            "authorized-purger",
            ("market", "view_listing"),
            ("market", "delete_listing"),
            ("market", "purge_listing"),
        )
        authorized_request = self._admin_request(authorized)
        self.assertTrue(self.listing_admin.has_delete_permission(authorized_request, self.listing))
        self.assertIn("delete_selected", self.listing_admin.get_actions(authorized_request))

    def test_admin_image_replacement_and_single_delete_cleanup_files(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save("old.png", make_image("old.png"), save=True)
            storage = self.listing.image.storage
            old_name = self.listing.image.name
            self.assertTrue(storage.exists(old_name))

            form = ListingAdminForm(
                data=self._listing_form_data(self.listing),
                files={"image": make_image("replacement.png")},
                instance=self.listing,
            )
            self.assertTrue(form.is_valid(), form.errors.as_json())
            changed_listing = form.save(commit=False)

            with self.captureOnCommitCallbacks(execute=True):
                self.listing_admin.save_model(
                    self.request,
                    changed_listing,
                    form,
                    change=True,
                )

            changed_listing.refresh_from_db()
            new_name = changed_listing.image.name
            self.assertNotEqual(new_name, old_name)
            self.assertFalse(storage.exists(old_name))
            self.assertTrue(storage.exists(new_name))

            with self.captureOnCommitCallbacks(execute=True):
                self.listing_admin.delete_model(self.request, changed_listing)

            self.assertFalse(Listing.objects.filter(pk=changed_listing.pk).exists())
            self.assertFalse(storage.exists(new_name))

    def test_admin_image_replacement_retains_report_snapshot_evidence(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "admin-evidence.png",
                make_image("admin-evidence.png"),
                save=True,
            )
            self.listing.refresh_from_db()
            storage = self.listing.image.storage
            evidence_name = self.listing.image.name
            with storage.open(evidence_name, "rb") as source:
                evidence_bytes = source.read()

            self.client.force_login(self.bob)
            response = self.client.post(
                reverse("market:report_create") + f"?listing={self.listing.pk}",
                {
                    "category": Report.Category.PROHIBITED,
                    "details": "관리자 교체 전 원본 증거",
                },
            )
            self.assertEqual(response.status_code, 302)
            report = Report.objects.get(reporter=self.bob, listing=self.listing)

            form = ListingAdminForm(
                data=self._listing_form_data(self.listing),
                files={"image": make_image("admin-replacement.png")},
                instance=self.listing,
            )
            self.assertTrue(form.is_valid(), form.errors.as_json())
            changed_listing = form.save(commit=False)
            with self.captureOnCommitCallbacks(execute=True):
                self.listing_admin.save_model(
                    self.request,
                    changed_listing,
                    form,
                    change=True,
                )

            changed_listing.refresh_from_db()
            report.refresh_from_db()
            self.assertNotEqual(changed_listing.image.name, evidence_name)
            self.assertTrue(storage.exists(changed_listing.image.name))
            self.assertTrue(storage.exists(evidence_name))
            with storage.open(evidence_name, "rb") as retained:
                self.assertEqual(retained.read(), evidence_bytes)
            self.assertEqual(report.listing_image_name_snapshot, evidence_name)
            self.assertEqual(
                report.listing_image_sha256,
                hashlib.sha256(evidence_bytes).hexdigest(),
            )

    def test_admin_bulk_delete_cleanup_files(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            listings = []
            for index in range(2):
                listing = Listing.objects.create(
                    seller=self.alice,
                    title=f"관리자 일괄 삭제 {index}",
                    description="일괄 삭제 시 이미지도 정리되어야 합니다.",
                    price_points=1_000,
                    category=Listing.Category.OTHER,
                    condition=Listing.Condition.GOOD,
                    region="서울",
                )
                listing.image.save(
                    f"bulk-{index}.png",
                    make_image(f"bulk-{index}.png"),
                    save=True,
                )
                listings.append(listing)

            files = [(listing.image.storage, listing.image.name) for listing in listings]
            self.assertTrue(all(storage.exists(name) for storage, name in files))

            with self.captureOnCommitCallbacks(execute=True):
                self.listing_admin.delete_queryset(
                    self.request,
                    Listing.objects.filter(pk__in=[listing.pk for listing in listings]),
                )

            self.assertFalse(
                Listing.objects.filter(pk__in=[listing.pk for listing in listings]).exists()
            )
            self.assertTrue(all(not storage.exists(name) for storage, name in files))


class ReadOnlyMarketAdminSecurityTests(MarketTestCase):
    def setUp(self):
        super().setUp()
        self.administrator = get_user_model().objects.create_superuser(
            username="evidence-admin",
            password=PASSWORD,
        )
        self.request = RequestFactory().post("/admin/market/evidence/")
        self.request.user = self.administrator
        self.favorite = Favorite.objects.create(user=self.bob, listing=self.listing)
        self.conversation = Conversation.objects.create(
            listing=self.listing,
            buyer=self.bob,
            seller=self.alice,
        )
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.bob,
            body="원본 거래 대화 증거",
        )

    def test_server_authored_admin_records_are_fully_readonly(self):
        records = (
            (FavoriteAdmin(Favorite, admin.site), self.favorite),
            (ConversationAdmin(Conversation, admin.site), self.conversation),
            (MessageAdmin(Message, admin.site), self.message),
        )

        for model_admin, record in records:
            with self.subTest(model=record._meta.label):
                expected_fields = {field.name for field in record._meta.concrete_fields}
                self.assertEqual(
                    set(model_admin.get_readonly_fields(self.request, record)),
                    expected_fields,
                )
                self.assertFalse(model_admin.has_add_permission(self.request))
                self.assertFalse(model_admin.has_change_permission(self.request, record))
                self.assertFalse(model_admin.has_delete_permission(self.request, record))

    def test_forged_message_change_post_cannot_mutate_evidence(self):
        other_listing = Listing.objects.create(
            seller=self.eve,
            title="위조 대상 상품",
            description="관리자 위조 요청에 사용되는 다른 상품입니다.",
            price_points=2_000,
            category=Listing.Category.OTHER,
            condition=Listing.Condition.GOOD,
            region="부산",
        )
        other_conversation = Conversation.objects.create(
            listing=other_listing,
            buyer=self.bob,
            seller=self.eve,
        )
        original = {
            "conversation_id": self.message.conversation_id,
            "sender_id": self.message.sender_id,
            "body": self.message.body,
            "created_at": self.message.created_at,
        }
        original_conversation_updated_at = self.conversation.updated_at
        self.client.force_login(self.administrator)

        response = self.client.post(
            reverse("admin:market_message_change", args=[self.message.pk]),
            {
                "conversation": other_conversation.pk,
                "sender": self.eve.pk,
                "body": "위조된 거래 대화 증거",
                "created_at": "2000-01-01 00:00:00",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.message.refresh_from_db()
        self.conversation.refresh_from_db()
        for field, value in original.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(self.message, field), value)
        self.assertEqual(
            self.conversation.updated_at,
            original_conversation_updated_at,
        )


class ConversationSecurityTests(MarketTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.bob)
        self.client.post(reverse("market:conversation_start", args=[self.listing.pk]))
        self.conversation = Conversation.objects.get()

    def test_only_participants_can_read_conversation(self):
        self.client.force_login(self.eve)
        response = self.client.get(
            reverse("market:conversation_detail", args=[self.conversation.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_sender_is_derived_from_session_and_message_is_escaped(self):
        response = self.client.post(
            reverse("market:conversation_detail", args=[self.conversation.pk]),
            {"body": "<script>alert(1)</script>", "sender": self.alice.pk},
        )
        self.assertEqual(response.status_code, 302)
        message = Message.objects.get()
        self.assertEqual(message.sender, self.bob)

        detail = self.client.get(reverse("market:conversation_detail", args=[self.conversation.pk]))
        self.assertNotContains(detail, "<script>alert(1)</script>", html=False)
        self.assertContains(detail, "&lt;script&gt;", html=False)

    def test_blocked_users_cannot_send_messages(self):
        UserBlock.objects.create(blocker=self.alice, blocked=self.bob)
        response = self.client.post(
            reverse("market:conversation_detail", args=[self.conversation.pk]),
            {"body": "차단 우회"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Message.objects.exists())

    def test_sold_listing_cannot_start_a_new_conversation(self):
        self.conversation.delete()
        self.listing.status = Listing.Status.SOLD
        self.listing.save(update_fields=("status", "updated_at"))

        response = self.client.post(reverse("market:conversation_start", args=[self.listing.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Conversation.objects.exists())

    def test_blocked_listing_metadata_is_hidden_from_buyer_conversation(self):
        self.listing.status = Listing.Status.BLOCKED
        self.listing.save(update_fields=("status", "updated_at"))

        response = self.client.get(
            reverse("market:conversation_detail", args=[self.conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "운영 정책에 따라 비공개된 상품")
        self.assertNotContains(response, self.listing.title)
        self.assertFalse(response.context["listing_visible"])

    def test_conversation_list_uses_annotated_last_message(self):
        Message.objects.create(
            conversation=self.conversation,
            sender=self.bob,
            body="마지막 메시지 미리보기",
        )

        response = self.client.get(reverse("market:conversation_list"))

        self.assertEqual(response.status_code, 200)
        item = response.context["conversations"][0]
        self.assertEqual(item.last_message_body, "마지막 메시지 미리보기")
        self.assertEqual(item.last_message_sender, self.bob.username)

    def test_conversation_list_hides_nonpublic_listing_metadata(self):
        self.listing.image.name = "listings/private/secret.jpg"
        self.listing.save(update_fields=("image", "updated_at"))
        image_url = reverse("market:listing_image", args=[self.listing.pk])

        for status in (Listing.Status.BLOCKED, Listing.Status.DELETED):
            with self.subTest(status=status):
                self.listing.status = status
                self.listing.save(update_fields=("status", "updated_at"))

                response = self.client.get(reverse("market:conversation_list"))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "운영 정책에 따라 비공개된 상품")
                self.assertNotContains(response, self.listing.title)
                self.assertNotContains(response, image_url)
                self.assertNotContains(response, "<time", html=False)
                self.assertNotContains(
                    response,
                    (
                        f'<span class="status-pill status-{status.lower()}">'
                        f"{self.listing.get_status_display()}</span>"
                    ),
                    html=False,
                )
                item = response.context["conversations"][0]
                self.assertFalse(item.listing_visible)


class ModerationSecurityTests(MarketTestCase):
    def setUp(self):
        super().setUp()
        self.report_admin = ReportAdmin(Report, admin.site)
        self.request_factory = RequestFactory()

    def _moderator(self, username, *permissions):
        user = get_user_model().objects.create_user(
            username=username,
            password=PASSWORD,
            is_staff=True,
        )
        for app_label, codename in permissions:
            user.user_permissions.add(
                Permission.objects.get(
                    content_type__app_label=app_label,
                    codename=codename,
                )
            )
        return user

    def _admin_request(self, user):
        request = self.request_factory.post("/admin/market/report/")
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        return request

    @staticmethod
    def _reporter(username):
        return get_user_model().objects.create_user(username=username, password=PASSWORD)

    def _report_listing_as(self, reporter, *, follow=False):
        self.client.force_login(reporter)
        return self.client.post(
            reverse("market:report_create") + f"?listing={self.listing.pk}",
            {
                "category": Report.Category.FRAUD,
                "details": f"{reporter.username}의 독립적인 상품 신고",
            },
            follow=follow,
        )

    def _report_user_as(self, reporter, target, listing, *, follow=False):
        conversation = Conversation.objects.create(
            listing=listing,
            buyer=reporter,
            seller=target,
        )
        self.client.force_login(reporter)
        response = self.client.post(
            reverse("market:report_create") + f"?conversation={conversation.pk}",
            {
                "category": Report.Category.ABUSE,
                "details": f"{reporter.username}의 독립적인 사용자 신고",
            },
            follow=follow,
        )
        return response, conversation

    def test_report_target_is_server_selected_and_duplicate_is_limited(self):
        self.client.force_login(self.bob)
        url = reverse("market:report_create") + f"?listing={self.listing.pk}"
        data = {"category": Report.Category.FRAUD, "details": "사기 의심 정황"}
        first = self.client.post(url, data)
        second = self.client.post(url, data)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        report = Report.objects.get()
        self.assertEqual(report.reporter, self.bob)
        self.assertEqual(report.listing, self.listing)
        self.assertIsNone(report.target_user)

    def test_three_distinct_reporters_auto_block_listing_and_redirect_home(self):
        mallory = self._reporter("listing-threshold-third")

        first = self._report_listing_as(self.bob)
        duplicate = self._report_listing_as(self.bob)
        second = self._report_listing_as(self.eve)
        self.listing.refresh_from_db()

        self.assertEqual(first.status_code, 302)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
        self.assertEqual(
            Report.objects.filter(listing=self.listing).values("reporter_id").distinct().count(),
            2,
        )

        with self.assertLogs("tiny_market.security", level="WARNING"):
            third = self._report_listing_as(mallory, follow=True)

        self.listing.refresh_from_db()
        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.redirect_chain, [(reverse("market:home"), 302)])
        self.assertContains(third, "임시 비공개 처리했습니다")
        self.assertNotContains(third, self.listing.title)
        self.assertEqual(self.listing.status, Listing.Status.BLOCKED)
        self.assertIsNone(self.listing.blocked_by)
        self.assertEqual(self.listing.blocked_reason, AUTOMATIC_LISTING_BLOCK_REASON)
        self.assertIsNotNone(self.listing.blocked_at)
        self.assertEqual(
            Report.objects.filter(listing=self.listing, status=Report.Status.OPEN)
            .values("reporter_id")
            .distinct()
            .count(),
            3,
        )
        self.assertEqual(
            self.client.get(reverse("market:listing_detail", args=[self.listing.pk])).status_code,
            404,
        )

    def test_three_distinct_user_reports_auto_suspend_and_keep_safe_redirect(self):
        mallory = self._reporter("user-threshold-third")
        # A self-authored row cannot be created by the web route and must not
        # contribute to the automatic threshold even if inserted internally.
        Report.objects.create(
            reporter=self.alice,
            target_user=self.alice,
            category=Report.Category.OTHER,
            details="자기 자신에 대한 내부 신고 행",
        )

        self._report_user_as(self.bob, self.alice, self.listing)
        self._report_user_as(self.eve, self.alice, self.listing)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.is_active)
        self.assertFalse(self.alice.is_suspended)

        with self.assertLogs("tiny_market.security", level="WARNING"):
            third, conversation = self._report_user_as(
                mallory,
                self.alice,
                self.listing,
                follow=True,
            )

        self.alice.refresh_from_db()
        self.assertEqual(third.status_code, 200)
        self.assertEqual(
            third.redirect_chain,
            [(reverse("market:conversation_detail", args=[conversation.pk]), 302)],
        )
        self.assertContains(third, "상대 계정을 임시 정지했습니다")
        self.assertFalse(third.context["interaction_allowed"])
        self.assertTrue(self.alice.is_suspended)
        self.assertFalse(self.alice.is_active)
        self.assertEqual(self.alice.suspension_reason, AUTOMATIC_USER_SUSPENSION_REASON)
        self.assertIsNotNone(self.alice.suspended_at)
        self.assertEqual(
            Report.objects.filter(target_user=self.alice, status=Report.Status.OPEN)
            .exclude(reporter=self.alice)
            .values("reporter_id")
            .distinct()
            .count(),
            3,
        )

    def test_automatic_user_threshold_never_suspends_staff_or_superuser(self):
        mallory = self._reporter("protected-threshold-third")
        protected_users = (
            get_user_model().objects.create_user(
                username="automatic-protected-staff",
                password=PASSWORD,
                is_staff=True,
            ),
            get_user_model().objects.create_superuser(
                username="automatic-protected-superuser",
                password=PASSWORD,
            ),
        )

        for index, target in enumerate(protected_users):
            with self.subTest(target=target.username):
                listing = Listing.objects.create(
                    seller=target,
                    title=f"보호 계정 신고 상품 {index}",
                    description="보호 계정 자동 정지 제외 검사",
                    price_points=1_000,
                    category=Listing.Category.OTHER,
                    condition=Listing.Condition.GOOD,
                    region="서울",
                )
                self._report_user_as(self.bob, target, listing)
                self._report_user_as(self.eve, target, listing)
                with self.assertLogs("tiny_market.security", level="WARNING"):
                    response, conversation = self._report_user_as(
                        mallory,
                        target,
                        listing,
                        follow=True,
                    )

                target.refresh_from_db()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    response.redirect_chain,
                    [(reverse("market:conversation_detail", args=[conversation.pk]), 302)],
                )
                self.assertTrue(target.is_active)
                self.assertFalse(target.is_suspended)
                self.assertEqual(
                    Report.objects.filter(target_user=target, status=Report.Status.OPEN).count(),
                    3,
                )

    def test_listing_report_captures_exact_snapshot_and_image_sha256(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "report-evidence.png",
                make_image("report-evidence.png"),
                save=True,
            )
            self.listing.refresh_from_db()
            image_name = self.listing.image.name
            with self.listing.image.storage.open(image_name, "rb") as stored_image:
                expected_sha256 = hashlib.sha256(stored_image.read()).hexdigest()

            self.client.force_login(self.bob)
            response = self.client.post(
                reverse("market:report_create") + f"?listing={self.listing.pk}",
                {
                    "category": Report.Category.FRAUD,
                    "details": "이미지와 상품 정보 증거 보존 요청",
                },
            )

            self.assertRedirects(
                response,
                reverse("market:listing_detail", args=[self.listing.pk]),
            )
            report = Report.objects.get(reporter=self.bob, listing=self.listing)
            expected_snapshot = {
                "listing_title_snapshot": self.listing.title,
                "listing_description_snapshot": self.listing.description,
                "listing_price_snapshot": self.listing.price_points,
                "listing_category_snapshot": self.listing.category,
                "listing_condition_snapshot": self.listing.condition,
                "listing_region_snapshot": self.listing.region,
                "listing_status_snapshot": self.listing.status,
                "listing_image_name_snapshot": image_name,
                "listing_image_sha256": expected_sha256,
            }
            for field, value in expected_snapshot.items():
                with self.subTest(field=field):
                    self.assertEqual(getattr(report, field), value)
            self.assertEqual(len(report.listing_image_sha256), 64)

    def test_authorized_admin_can_view_verified_private_evidence_image(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "reviewable-evidence.png",
                make_image("reviewable-evidence.png"),
                save=True,
            )
            self.listing.refresh_from_db()
            self.client.force_login(self.bob)
            self.client.post(
                reverse("market:report_create") + f"?listing={self.listing.pk}",
                {
                    "category": Report.Category.PROHIBITED,
                    "details": "관리자 증거 이미지 조회",
                },
            )
            report = Report.objects.get(reporter=self.bob, listing=self.listing)
            with self.listing.image.storage.open(
                report.listing_image_name_snapshot,
                "rb",
            ) as source:
                expected_bytes = source.read()

            reviewer = self._moderator(
                "evidence-reviewer",
                ("market", "view_report"),
            )
            self.client.force_login(reviewer)
            evidence_url = reverse(
                "admin:market_report_evidence_image",
                args=[report.pk],
            )
            with self.assertLogs("tiny_market.security", level="INFO"):
                response = self.client.get(evidence_url)

            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), expected_bytes)
            self.assertEqual(response.headers["Content-Type"], "image/jpeg")
            self.assertEqual(response.headers["Cache-Control"], "private, no-store")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertIn(evidence_url, str(self.report_admin.listing_image_evidence_link(report)))

    def test_evidence_endpoint_hides_ids_and_rejects_tampered_file(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "tamper-evidence.png",
                make_image("tamper-evidence.png"),
                save=True,
            )
            self.listing.refresh_from_db()
            self.client.force_login(self.bob)
            self.client.post(
                reverse("market:report_create") + f"?listing={self.listing.pk}",
                {
                    "category": Report.Category.FRAUD,
                    "details": "증거 무결성 실패 검사",
                },
            )
            report = Report.objects.get(reporter=self.bob, listing=self.listing)
            evidence_url = reverse(
                "admin:market_report_evidence_image",
                args=[report.pk],
            )

            unauthorized = self._moderator("no-report-view")
            self.client.force_login(unauthorized)
            self.assertEqual(self.client.get(evidence_url).status_code, 403)
            missing_url = reverse(
                "admin:market_report_evidence_image",
                args=[report.pk + 10_000],
            )
            self.assertEqual(self.client.get(missing_url).status_code, 403)

            reviewer = self._moderator(
                "tamper-reviewer",
                ("market", "view_report"),
            )
            storage = self.listing.image.storage
            with storage.open(report.listing_image_name_snapshot, "wb") as destination:
                destination.write(b"tampered-evidence")
            self.client.force_login(reviewer)
            with self.assertLogs("tiny_market.security", level="WARNING"):
                tampered = self.client.get(evidence_url)
            self.assertEqual(tampered.status_code, 404)

    def test_reported_listing_can_change_while_original_image_evidence_stays_private(self):
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            self.listing.image.save(
                "original-evidence.png",
                make_image("original-evidence.png"),
                save=True,
            )
            self.listing.refresh_from_db()
            storage = self.listing.image.storage
            original_image_name = self.listing.image.name
            with storage.open(original_image_name, "rb") as original_file:
                original_image_bytes = original_file.read()
            self.client.force_login(self.bob)
            report_response = self.client.post(
                reverse("market:report_create") + f"?listing={self.listing.pk}",
                {
                    "category": Report.Category.PROHIBITED,
                    "details": "신고 후 원본 증거 보존 검사",
                },
            )
            self.assertEqual(report_response.status_code, 302)
            report = Report.objects.get(reporter=self.bob, listing=self.listing)
            original_snapshot = {
                field: getattr(report, field)
                for field in (
                    "listing_title_snapshot",
                    "listing_description_snapshot",
                    "listing_price_snapshot",
                    "listing_category_snapshot",
                    "listing_condition_snapshot",
                    "listing_region_snapshot",
                    "listing_status_snapshot",
                    "listing_image_name_snapshot",
                    "listing_image_sha256",
                )
            }
            self.assertEqual(
                report.listing_image_sha256,
                hashlib.sha256(original_image_bytes).hexdigest(),
            )
            update_url = reverse("market:listing_update", args=[self.listing.pk])
            delete_url = reverse("market:listing_delete", args=[self.listing.pk])
            status_url = reverse(
                "market:listing_status_update",
                args=[self.listing.pk],
            )
            self.client.force_login(self.alice)

            self.assertEqual(self.client.get(update_url).status_code, 200)
            with self.captureOnCommitCallbacks(execute=True):
                update_response = self.client.post(
                    update_url,
                    {
                        "title": "신고 후 정상 변경 제목",
                        "description": "신고 검토와 별개로 판매자는 상품을 수정할 수 있습니다.",
                        "price_points": 31_000,
                        "category": Listing.Category.OTHER,
                        "condition": Listing.Condition.FAIR,
                        "region": "변경 지역",
                        "image": make_image("replacement.png"),
                    },
                )
            self.assertEqual(update_response.status_code, 302)

            self.listing.refresh_from_db()
            current_image_name = self.listing.image.name
            self.assertEqual(self.listing.title, "신고 후 정상 변경 제목")
            self.assertNotEqual(current_image_name, original_image_name)
            self.assertTrue(storage.exists(current_image_name))
            self.assertTrue(storage.exists(original_image_name))
            report.refresh_from_db()
            for field, value in original_snapshot.items():
                with self.subTest(field=field):
                    self.assertEqual(getattr(report, field), value)

            self.client.logout()
            current_image_response = self.client.get(
                reverse("market:listing_image", args=[self.listing.pk])
            )
            self.assertEqual(current_image_response.status_code, 200)
            current_image_bytes = b"".join(current_image_response.streaming_content)
            self.assertNotEqual(
                hashlib.sha256(current_image_bytes).hexdigest(),
                report.listing_image_sha256,
            )
            evidence_public_url = f"{settings.MEDIA_URL}{original_image_name}"
            self.assertEqual(self.client.get(evidence_public_url).status_code, 404)

            self.client.force_login(self.alice)
            status_response = self.client.post(
                status_url,
                {"status": Listing.Status.RESERVED},
            )
            self.assertEqual(status_response.status_code, 302)
            self.assertEqual(self.client.get(delete_url).status_code, 200)
            with self.captureOnCommitCallbacks(execute=True):
                delete_response = self.client.post(delete_url)
            self.assertEqual(delete_response.status_code, 302)

            self.listing.refresh_from_db()
            report.refresh_from_db()
            self.assertEqual(self.listing.status, Listing.Status.DELETED)
            self.assertFalse(self.listing.image)
            self.assertFalse(storage.exists(current_image_name))
            self.assertTrue(storage.exists(original_image_name))
            with storage.open(original_image_name, "rb") as retained_evidence:
                self.assertEqual(retained_evidence.read(), original_image_bytes)
            for field, value in original_snapshot.items():
                with self.subTest(field=field):
                    self.assertEqual(getattr(report, field), value)
            self.assertEqual(
                self.client.get(
                    reverse("market:listing_image", args=[self.listing.pk])
                ).status_code,
                404,
            )
            self.assertEqual(self.client.get(evidence_public_url).status_code, 404)

    def test_user_report_target_is_derived_from_participant_conversation(self):
        self.client.force_login(self.bob)
        self.client.post(reverse("market:conversation_start", args=[self.listing.pk]))
        conversation = Conversation.objects.get()

        response = self.client.post(
            reverse("market:report_create") + f"?conversation={conversation.pk}",
            {"category": Report.Category.ABUSE, "details": "대화 중 위협적인 표현"},
        )

        self.assertRedirects(
            response,
            reverse("market:conversation_detail", args=[conversation.pk]),
        )
        report = Report.objects.get()
        self.assertEqual(report.target_user, self.alice)
        self.assertIsNone(report.listing)

    def test_arbitrary_sequential_user_id_cannot_be_reported(self):
        self.client.force_login(self.bob)

        response = self.client.get(reverse("market:report_create") + f"?user={self.eve.pk}")

        self.assertEqual(response.status_code, 404)

    def test_invalid_report_uuid_returns_not_found(self):
        self.client.force_login(self.bob)

        for query in (
            "?listing=not-a-uuid",
            f"?listing={'a' * 37}",
            "?conversation=not-a-uuid",
            f"?conversation={'a' * 37}",
        ):
            with self.subTest(query=query):
                response = self.client.get(reverse("market:report_create") + query)
                self.assertEqual(response.status_code, 404)

    def test_staff_and_superuser_counterparts_can_be_reported_without_auto_suspension(self):
        self.client.force_login(self.bob)
        protected_users = (
            get_user_model().objects.create_user(
                username="reported-staff",
                password=PASSWORD,
                is_staff=True,
            ),
            get_user_model().objects.create_superuser(
                username="reported-superuser",
                password=PASSWORD,
            ),
        )

        for index, target in enumerate(protected_users):
            with self.subTest(target=target.username):
                listing = Listing.objects.create(
                    seller=target,
                    title=f"보호 계정 상품 {index}",
                    description="보호 계정도 대화 증거를 통해 신고할 수 있어야 합니다.",
                    price_points=1_000,
                    category=Listing.Category.OTHER,
                    condition=Listing.Condition.GOOD,
                    region="서울",
                )
                conversation = Conversation.objects.create(
                    listing=listing,
                    buyer=self.bob,
                    seller=target,
                )

                response = self.client.post(
                    reverse("market:report_create") + f"?conversation={conversation.pk}",
                    {
                        "category": Report.Category.ABUSE,
                        "details": "관리자 계정의 대화도 검토가 필요합니다.",
                    },
                )

                self.assertRedirects(
                    response,
                    reverse("market:conversation_detail", args=[conversation.pk]),
                )
                report = Report.objects.get(reporter=self.bob, target_user=target)
                target.refresh_from_db()
                self.assertEqual(report.status, Report.Status.OPEN)
                self.assertIsNone(report.resolver)
                self.assertTrue(target.is_active)
                self.assertFalse(target.is_suspended)

    def test_report_admin_evidence_is_readonly_and_cannot_be_added_or_deleted(self):
        moderator = self._moderator(
            "evidence-moderator",
            ("market", "view_report"),
            ("market", "change_report"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.FRAUD,
            details="보존해야 하는 신고 증거",
        )
        request = self._admin_request(moderator)
        expected_readonly = {
            "reporter",
            "target_user",
            "listing",
            "category",
            "details",
            "listing_title_snapshot",
            "listing_description_snapshot",
            "listing_price_snapshot",
            "listing_category_snapshot",
            "listing_condition_snapshot",
            "listing_region_snapshot",
            "listing_status_snapshot",
            "listing_image_name_snapshot",
            "listing_image_sha256",
            "status",
            "resolver",
            "created_at",
            "updated_at",
            "resolved_at",
        }

        self.assertTrue(
            expected_readonly.issubset(set(self.report_admin.get_readonly_fields(request, report)))
        )
        self.assertFalse(self.report_admin.has_add_permission(request))
        self.assertFalse(self.report_admin.has_delete_permission(request, report))

    def test_forged_report_change_post_cannot_mutate_evidence(self):
        administrator = get_user_model().objects.create_superuser(
            username="report-evidence-admin",
            password=PASSWORD,
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.FRAUD,
            details="원본 신고 증거",
            listing_title_snapshot="원본 상품 제목",
            listing_description_snapshot="원본 상품 설명",
            listing_price_snapshot=30_000,
            listing_category_snapshot=Listing.Category.ELECTRONICS,
            listing_condition_snapshot=Listing.Condition.GOOD,
            listing_region_snapshot="서울 마포구",
            listing_status_snapshot=Listing.Status.ACTIVE,
            listing_image_name_snapshot="listings/evidence/original.jpg",
            listing_image_sha256="a" * 64,
        )
        original = {
            "reporter_id": report.reporter_id,
            "target_user_id": report.target_user_id,
            "listing_id": report.listing_id,
            "category": report.category,
            "details": report.details,
            "listing_title_snapshot": report.listing_title_snapshot,
            "listing_description_snapshot": report.listing_description_snapshot,
            "listing_price_snapshot": report.listing_price_snapshot,
            "listing_category_snapshot": report.listing_category_snapshot,
            "listing_condition_snapshot": report.listing_condition_snapshot,
            "listing_region_snapshot": report.listing_region_snapshot,
            "listing_status_snapshot": report.listing_status_snapshot,
            "listing_image_name_snapshot": report.listing_image_name_snapshot,
            "listing_image_sha256": report.listing_image_sha256,
            "status": report.status,
            "resolver_id": report.resolver_id,
            "resolved_at": report.resolved_at,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
        }
        self.client.force_login(administrator)

        response = self.client.post(
            reverse("admin:market_report_change", args=[report.pk]),
            {
                "reporter": self.eve.pk,
                "target_user": self.eve.pk,
                "listing": "",
                "category": Report.Category.ABUSE,
                "details": "위조된 신고 내용",
                "listing_title_snapshot": "위조된 상품 제목",
                "listing_description_snapshot": "위조된 상품 설명",
                "listing_price_snapshot": 1,
                "listing_category_snapshot": Listing.Category.OTHER,
                "listing_condition_snapshot": Listing.Condition.FAIR,
                "listing_region_snapshot": "위조 지역",
                "listing_status_snapshot": Listing.Status.SOLD,
                "listing_image_name_snapshot": "listings/forged.jpg",
                "listing_image_sha256": "b" * 64,
                "status": Report.Status.RESOLVED,
                "resolver": administrator.pk,
                "resolved_at": "2000-01-01 00:00:00",
                "created_at": "2000-01-01 00:00:00",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 403)
        report.refresh_from_db()
        for field, value in original.items():
            with self.subTest(field=field):
                self.assertEqual(getattr(report, field), value)

    def test_nonpublic_listing_metadata_cannot_be_reopened_via_report(self):
        self.listing.status = Listing.Status.BLOCKED
        self.listing.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.bob)

        response = self.client.get(reverse("market:report_create") + f"?listing={self.listing.pk}")

        self.assertEqual(response.status_code, 404)

    def test_report_requires_exactly_one_target_at_database_level(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Report.objects.create(
                    reporter=self.bob,
                    category=Report.Category.SPAM,
                    details="invalid",
                )

    def test_database_allows_only_one_open_report_per_reporter_and_target(self):
        target_cases = (
            {"listing": self.listing},
            {"target_user": self.eve},
        )

        for target in target_cases:
            with self.subTest(target=target):
                first = Report.objects.create(
                    reporter=self.bob,
                    category=Report.Category.FRAUD,
                    details="첫 번째 미처리 신고",
                    **target,
                )
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        Report.objects.create(
                            reporter=self.bob,
                            category=Report.Category.FRAUD,
                            details="중복 미처리 신고",
                            **target,
                        )

                first.status = Report.Status.RESOLVED
                first.save(update_fields=("status", "updated_at"))
                second = Report.objects.create(
                    reporter=self.bob,
                    category=Report.Category.FRAUD,
                    details="기존 처리 후 새 신고",
                    **target,
                )
                self.assertEqual(second.status, Report.Status.OPEN)

    def test_non_staff_user_cannot_access_admin(self):
        self.client.force_login(self.bob)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)

    def test_user_block_next_parameter_cannot_open_redirect(self):
        self.client.force_login(self.bob)
        Conversation.objects.create(
            listing=self.listing,
            buyer=self.bob,
            seller=self.alice,
        )
        response = self.client.post(
            reverse("market:user_block_toggle", args=[self.alice.pk]),
            {"next": "//evil.example/phish"},
        )
        self.assertRedirects(response, reverse("market:conversation_list"))

    def test_unrelated_user_cannot_be_enumerated_through_block_action(self):
        self.client.force_login(self.bob)

        response = self.client.post(reverse("market:user_block_toggle", args=[self.eve.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(UserBlock.objects.filter(blocker=self.bob, blocked=self.eve).exists())

    def test_listing_block_action_requires_dedicated_block_permission(self):
        moderator = self._moderator(
            "legacy-listing-editor",
            ("market", "change_report"),
            ("market", "change_listing"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.PROHIBITED,
            details="금지 품목 의심",
        )
        request = self._admin_request(moderator)

        self.assertNotIn(
            "block_reported_listings",
            self.report_admin.get_actions(request),
        )
        self.assertNotIn(
            "restore_auto_blocked_listings",
            self.report_admin.get_actions(request),
        )
        with self.assertRaises(PermissionDenied):
            self.report_admin.block_reported_listings(
                request,
                Report.objects.filter(pk=report.pk),
            )
        with self.assertRaises(PermissionDenied):
            self.report_admin.restore_auto_blocked_listings(
                request,
                Report.objects.filter(pk=report.pk),
            )

        self.listing.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_forged_admin_post_cannot_bypass_listing_permission(self):
        moderator = self._moderator(
            "post-forger",
            ("market", "change_report"),
            ("market", "change_listing"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.FRAUD,
            details="권한 우회 시도",
        )
        self.client.force_login(moderator)

        self.client.post(
            reverse("admin:market_report_changelist"),
            {
                "action": "block_reported_listings",
                "_selected_action": [str(report.pk)],
                "select_across": "0",
                "index": "0",
            },
        )

        self.listing.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_listing_block_action_with_report_and_block_permissions_succeeds(self):
        moderator = self._moderator(
            "listing-moderator",
            ("market", "change_report"),
            ("market", "block_listing"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.PROHIBITED,
            details="차단할 상품",
        )

        self.report_admin.block_reported_listings(
            self._admin_request(moderator),
            Report.objects.filter(pk=report.pk),
        )

        self.listing.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.BLOCKED)
        self.assertEqual(self.listing.blocked_by, moderator)
        self.assertEqual(report.status, Report.Status.RESOLVED)

    def test_authorized_admin_can_restore_only_automatic_listing_block(self):
        mallory = self._reporter("restore-auto-third")
        for reporter in (self.bob, self.eve, mallory):
            self._report_listing_as(reporter)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.BLOCKED)
        reports = Report.objects.filter(listing=self.listing)

        moderator = self._moderator(
            "automatic-block-reviewer",
            ("market", "change_report"),
            ("market", "block_listing"),
        )
        request = self._admin_request(moderator)
        self.assertIn("restore_auto_blocked_listings", self.report_admin.get_actions(request))

        with self.assertLogs("tiny_market.security", level="WARNING"):
            self.report_admin.restore_auto_blocked_listings(request, reports)

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.ACTIVE)
        self.assertIsNone(self.listing.blocked_by)
        self.assertEqual(self.listing.blocked_reason, "")
        self.assertIsNone(self.listing.blocked_at)
        self.assertEqual(reports.filter(status=Report.Status.DISMISSED).count(), 3)
        self.assertFalse(reports.filter(status=Report.Status.OPEN).exists())
        self.assertFalse(reports.exclude(resolver=moderator).exists())

    def test_restore_action_does_not_reopen_manually_blocked_listing(self):
        moderator = self._moderator(
            "manual-block-reviewer",
            ("market", "change_report"),
            ("market", "block_listing"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            listing=self.listing,
            category=Report.Category.PROHIBITED,
            details="수동 차단은 자동 복구 대상이 아닙니다.",
        )
        self.listing.status = Listing.Status.BLOCKED
        self.listing.blocked_by = moderator
        self.listing.blocked_reason = "관리자 수동 차단"
        self.listing.blocked_at = timezone.now()
        self.listing.save(
            update_fields=(
                "status",
                "blocked_by",
                "blocked_reason",
                "blocked_at",
                "updated_at",
            )
        )

        self.report_admin.restore_auto_blocked_listings(
            self._admin_request(moderator),
            Report.objects.filter(pk=report.pk),
        )

        self.listing.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.BLOCKED)
        self.assertEqual(self.listing.blocked_by, moderator)
        self.assertEqual(self.listing.blocked_reason, "관리자 수동 차단")
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_user_suspend_action_requires_dedicated_suspend_permission(self):
        moderator = self._moderator(
            "no-user-permission",
            ("market", "change_report"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            target_user=self.eve,
            category=Report.Category.ABUSE,
            details="사용자 신고",
        )
        request = self._admin_request(moderator)

        self.assertNotIn(
            "suspend_reported_users",
            self.report_admin.get_actions(request),
        )
        with self.assertRaises(PermissionDenied):
            self.report_admin.suspend_reported_users(
                request,
                Report.objects.filter(pk=report.pk),
            )

        self.eve.refresh_from_db()
        report.refresh_from_db()
        self.assertFalse(self.eve.is_suspended)
        self.assertTrue(self.eve.is_active)
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_forged_admin_post_cannot_bypass_suspend_permission(self):
        moderator = self._moderator(
            "user-post-forger",
            ("market", "change_report"),
        )
        report = Report.objects.create(
            reporter=self.bob,
            target_user=self.eve,
            category=Report.Category.ABUSE,
            details="사용자 정지 권한 우회 시도",
        )
        self.client.force_login(moderator)

        self.client.post(
            reverse("admin:market_report_changelist"),
            {
                "action": "suspend_reported_users",
                "_selected_action": [str(report.pk)],
                "select_across": "0",
                "index": "0",
            },
        )

        self.eve.refresh_from_db()
        report.refresh_from_db()
        self.assertFalse(self.eve.is_suspended)
        self.assertTrue(self.eve.is_active)
        self.assertEqual(report.status, Report.Status.OPEN)

    def test_user_suspend_action_skips_self_staff_and_superusers(self):
        moderator = self._moderator(
            "user-moderator",
            ("market", "change_report"),
            ("accounts", "suspend_user"),
        )
        staff_target = get_user_model().objects.create_user(
            username="staff-report-target",
            password=PASSWORD,
            is_staff=True,
        )
        superuser_target = get_user_model().objects.create_superuser(
            username="superuser-report-target",
            password=PASSWORD,
        )
        reports = {
            target.pk: Report.objects.create(
                reporter=self.bob,
                target_user=target,
                category=Report.Category.ABUSE,
                details="계정 정지 검토",
            )
            for target in (self.eve, moderator, staff_target, superuser_target)
        }

        self.report_admin.suspend_reported_users(
            self._admin_request(moderator),
            Report.objects.filter(pk__in=[report.pk for report in reports.values()]),
        )

        self.eve.refresh_from_db()
        self.assertTrue(self.eve.is_suspended)
        self.assertFalse(self.eve.is_active)
        reports[self.eve.pk].refresh_from_db()
        self.assertEqual(reports[self.eve.pk].status, Report.Status.RESOLVED)

        for protected in (moderator, staff_target, superuser_target):
            protected.refresh_from_db()
            reports[protected.pk].refresh_from_db()
            self.assertFalse(protected.is_suspended)
            self.assertTrue(protected.is_active)
            self.assertEqual(reports[protected.pk].status, Report.Status.OPEN)


class WalletLedgerSecurityTests(MarketTestCase):
    def test_issuance_history_is_labeled_as_system_not_empty_username(self):
        self.client.force_login(self.alice)

        response = self.client.get(reverse("market:wallet"))

        self.assertContains(response, "시스템에서 교육용 포인트 지급")
        self.assertNotContains(response, "님에게 받음")

    def test_transfer_page_uses_authenticated_wallet_balance(self):
        self.client.force_login(self.alice)

        response = self.client.get(reverse("market:transfer"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["wallet"].owner, self.alice)
        self.assertEqual(response.context["wallet"].balance_cache, 100_000)

    def test_transfer_is_balanced_and_updates_both_wallets(self):
        transfer = transfer_points(self.alice, self.bob, 20_000, uuid.uuid4())

        self.alice.wallet.refresh_from_db()
        self.bob.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.balance_cache, 80_000)
        self.assertEqual(self.bob.wallet.balance_cache, 120_000)
        entries = transfer.entries.all()
        self.assertEqual(entries.count(), 2)
        self.assertEqual(sum(entries.values_list("delta", flat=True)), 0)

    def test_every_posted_transfer_has_exactly_two_balanced_entries(self):
        transfer_points(self.alice, self.bob, 20_000, uuid.uuid4())

        for transfer in Transfer.objects.all():
            entries = transfer.entries.all()
            self.assertEqual(entries.count(), 2)
            self.assertEqual(sum(entries.values_list("delta", flat=True)), 0)

    def test_transfer_instance_cannot_be_updated_or_deleted(self):
        posted = transfer_points(self.alice, self.bob, 10_000, uuid.uuid4())
        original_amount = posted.amount
        posted.amount = 1

        with self.assertRaises(ImmutableLedgerError):
            posted.save(update_fields=("amount",))
        with self.assertRaises(ImmutableLedgerError):
            posted.delete()

        posted.refresh_from_db()
        self.assertEqual(posted.amount, original_amount)
        self.assertTrue(Transfer.objects.filter(pk=posted.pk).exists())

    def test_transfer_queryset_cannot_be_updated_or_deleted(self):
        posted = transfer_points(self.alice, self.bob, 10_000, uuid.uuid4())
        queryset = Transfer.objects.filter(pk=posted.pk)

        with self.assertRaises(ImmutableLedgerError):
            queryset.update(amount=1)
        with self.assertRaises(ImmutableLedgerError):
            queryset.delete()

        self.assertEqual(Transfer.objects.get(pk=posted.pk).amount, 10_000)

    def test_ledger_entry_instance_cannot_be_updated_or_deleted(self):
        posted = transfer_points(self.alice, self.bob, 10_000, uuid.uuid4())
        entry = posted.entries.first()
        original_delta = entry.delta
        entry.delta = 1

        with self.assertRaises(ImmutableLedgerError):
            entry.save(update_fields=("delta",))
        with self.assertRaises(ImmutableLedgerError):
            entry.delete()

        entry.refresh_from_db()
        self.assertEqual(entry.delta, original_delta)
        self.assertTrue(LedgerEntry.objects.filter(pk=entry.pk).exists())

    def test_ledger_entry_queryset_cannot_be_updated_or_deleted(self):
        posted = transfer_points(self.alice, self.bob, 10_000, uuid.uuid4())
        entry = posted.entries.first()
        queryset = LedgerEntry.objects.filter(pk=entry.pk)

        with self.assertRaises(ImmutableLedgerError):
            queryset.update(delta=1)
        with self.assertRaises(ImmutableLedgerError):
            queryset.delete()

        self.assertEqual(LedgerEntry.objects.get(pk=entry.pk).delta, entry.delta)

    def test_same_idempotency_key_posts_only_once(self):
        key = uuid.uuid4()
        first = transfer_points(self.alice, self.bob, 10_000, key)
        second = transfer_points(self.alice, self.bob, 10_000, key)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Transfer.objects.filter(kind=Transfer.Kind.USER_TRANSFER).count(), 1)
        self.alice.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.balance_cache, 90_000)

    def test_reused_key_with_different_payload_is_rejected(self):
        key = uuid.uuid4()
        transfer_points(self.alice, self.bob, 10_000, key)
        with self.assertRaises(IdempotencyConflictError):
            transfer_points(self.alice, self.bob, 20_000, key)

    def test_insufficient_funds_rolls_back_entire_transfer(self):
        before_transfers = Transfer.objects.count()
        before_entries = LedgerEntry.objects.count()

        with self.assertRaises(InsufficientFundsError):
            transfer_points(self.alice, self.bob, 200_000, uuid.uuid4())

        self.alice.wallet.refresh_from_db()
        self.bob.wallet.refresh_from_db()
        self.assertEqual(self.alice.wallet.balance_cache, 100_000)
        self.assertEqual(self.bob.wallet.balance_cache, 100_000)
        self.assertEqual(Transfer.objects.count(), before_transfers)
        self.assertEqual(LedgerEntry.objects.count(), before_entries)

    def test_blocked_users_cannot_transfer(self):
        UserBlock.objects.create(blocker=self.bob, blocked=self.alice)
        with self.assertRaises(ValidationError):
            transfer_points(self.alice, self.bob, 1_000, uuid.uuid4())

    def test_web_transfer_ignores_sender_tampering(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("market:transfer"),
            {
                "recipient_username": "bob",
                "amount": 1_000,
                "idempotency_key": uuid.uuid4(),
                "sender": self.eve.pk,
            },
        )
        self.assertRedirects(response, reverse("market:wallet"))
        posted = Transfer.objects.filter(kind=Transfer.Kind.USER_TRANSFER).get()
        self.assertEqual(posted.initiated_by, self.alice)
        self.assertEqual(posted.sender_account.owner, self.alice)

    def test_cached_balance_matches_all_ledger_entries(self):
        transfer_points(self.alice, self.bob, 3_000, uuid.uuid4())
        for wallet in WalletAccount.objects.all():
            expected = sum(wallet.ledger_entries.values_list("delta", flat=True))
            wallet.refresh_from_db()
            self.assertEqual(wallet.balance_cache, expected)


class SecurityHeaderTests(MarketTestCase):
    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
        TRUSTED_PROXY_IPS=frozenset({"10.0.0.10"}),
    )
    def test_forwarded_https_header_is_trusted_only_from_configured_proxy(self):
        untrusted = self.client.get(
            reverse("market:home"),
            REMOTE_ADDR="198.51.100.44",
            HTTP_X_FORWARDED_PROTO="https",
        )
        trusted = self.client.get(
            reverse("market:home"),
            REMOTE_ADDR="10.0.0.10",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(untrusted.status_code, 301)
        self.assertTrue(untrusted.headers["Location"].startswith("https://"))
        self.assertEqual(trusted.status_code, 200)

    def test_public_response_has_strict_security_headers(self):
        response = self.client.get(reverse("market:home"))
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])
        self.assertIn("payment=()", response.headers["Permissions-Policy"])
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

    def test_authenticated_response_is_not_cacheable(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("market:wallet"))
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")

    def test_anonymous_dynamic_listing_metadata_is_not_cacheable(self):
        for url in (
            reverse("market:home"),
            reverse("market:listing_detail", args=[self.listing.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.headers["Cache-Control"], "private, no-store")
                self.assertEqual(response.headers["Pragma"], "no-cache")
