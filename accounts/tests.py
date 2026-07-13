from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, connection, transaction
from django.test import Client, RequestFactory, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from market.models import WalletAccount

from .admin import LoginAttemptAdmin, UserAdmin, UserBlockAdmin
from .forms import LoginForm, ProfileForm
from .models import LoginAttempt, UserBlock
from .views import (
    LOGIN_ATTEMPT_RETENTION,
    _attempt_keys,
    _network_identifier,
    _purge_expired_login_attempts,
)

PASSWORD = "Correct-Horse-Battery-99!"
NEW_PASSWORD = "Changed-Correct-Horse-88!"


class SignupSecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_signup_normalizes_username_hashes_password_and_issues_demo_points(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "Alice",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertRedirects(response, reverse("accounts:login"))
        user = get_user_model().objects.get()
        self.assertEqual(user.username, "alice")
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)
        self.assertEqual(user.wallet.balance_cache, 100_000)
        self.assertEqual(user.wallet.kind, WalletAccount.Kind.USER)

    def test_public_signup_cannot_assign_privileges_or_suspension(self):
        self.client.post(
            reverse("accounts:signup"),
            {
                "username": "mallory",
                "password1": PASSWORD,
                "password2": PASSWORD,
                "is_staff": "on",
                "is_superuser": "on",
                "is_suspended": "on",
            },
        )

        user = get_user_model().objects.get(username="mallory")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_suspended)

    def test_case_insensitive_duplicate_username_is_rejected(self):
        get_user_model().objects.create_user(username="Alice", password=PASSWORD)

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "ALICE",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertTrue(response.context["form"].errors)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            reverse("accounts:signup"),
            {"username": "alice", "password1": "password", "password2": "password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user_model().objects.exists())

    def test_signup_is_rate_limited_by_hashed_network_identifier(self):
        for index in range(5):
            response = self.client.post(
                reverse("accounts:signup"),
                {
                    "username": f"member{index}",
                    "password1": PASSWORD,
                    "password2": PASSWORD,
                },
                REMOTE_ADDR="203.0.113.50",
            )
            self.assertEqual(response.status_code, 302)

        response = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "member6",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
            REMOTE_ADDR="203.0.113.50",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(get_user_model().objects.count(), 5)


class LoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(username="alice", password=PASSWORD)

    def test_username_is_case_insensitive_and_session_rotates(self):
        session = self.client.session
        session["pre_login"] = "value"
        session.save()
        old_key = session.session_key

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "ALICE", "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("market:home"))
        self.assertNotEqual(old_key, self.client.session.session_key)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)

    def test_external_next_url_is_not_followed(self):
        response = self.client.post(
            reverse("accounts:login") + "?next=https://evil.example/phish",
            {"username": "alice", "password": PASSWORD},
        )

        self.assertRedirects(response, reverse("market:home"))

    def test_five_failures_lock_account_scope(self):
        for _index in range(5):
            response = self.client.post(
                reverse("accounts:login"),
                {"username": "alice", "password": "wrong-password"},
                REMOTE_ADDR="203.0.113.10",
            )
            self.assertEqual(response.status_code, 200)

        account_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.ACCOUNT)
        network_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.NETWORK)
        self.assertIsNotNone(account_attempt.locked_until)
        self.assertEqual(account_attempt.failures, 5)
        self.assertIsNone(network_attempt.locked_until)
        self.assertEqual(network_attempt.failures, 5)
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": PASSWORD},
            REMOTE_ADDR="203.0.113.10",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_successful_login_clears_only_account_attempt_record(self):
        self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": "wrong-password"},
            REMOTE_ADDR="203.0.113.11",
        )
        self.assertTrue(LoginAttempt.objects.exists())

        self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": PASSWORD},
            REMOTE_ADDR="203.0.113.11",
        )
        self.assertFalse(LoginAttempt.objects.filter(scope=LoginAttempt.Scope.ACCOUNT).exists())
        network_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.NETWORK)
        self.assertEqual(network_attempt.failures, 2)

    def test_successful_login_does_not_reset_network_attempt_counter(self):
        remote_address = "203.0.113.15"
        request = RequestFactory().post("/accounts/login/", REMOTE_ADDR=remote_address)
        alice_attempt_keys = dict(_attempt_keys(request, "alice"))
        primary_network_key = alice_attempt_keys[LoginAttempt.Scope.NETWORK]
        alice_account_key = alice_attempt_keys[LoginAttempt.Scope.ACCOUNT]
        for index in range(4):
            self.client.post(
                reverse("accounts:login"),
                {
                    "username": f"unknown-user-{index}",
                    "password": "wrong-password",
                },
                REMOTE_ADDR=remote_address,
            )

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": PASSWORD},
            REMOTE_ADDR=remote_address,
        )
        self.assertRedirects(response, reverse("market:home"))
        self.assertFalse(
            LoginAttempt.objects.filter(
                scope=LoginAttempt.Scope.ACCOUNT,
                key_hash=alice_account_key,
            ).exists()
        )
        self.assertEqual(
            LoginAttempt.objects.filter(scope=LoginAttempt.Scope.ACCOUNT).count(),
            4,
        )
        self.assertEqual(
            LoginAttempt.objects.get(
                scope=LoginAttempt.Scope.NETWORK,
                key_hash=primary_network_key,
            ).failures,
            5,
        )

        self.client.logout()
        self.client.post(
            reverse("accounts:login"),
            {"username": "another-unknown", "password": "wrong-password"},
            REMOTE_ADDR=remote_address,
        )
        self.assertEqual(
            LoginAttempt.objects.get(
                scope=LoginAttempt.Scope.NETWORK,
                key_hash=primary_network_key,
            ).failures,
            6,
        )

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_network_limit_bounds_new_account_attempt_rows_to_thirty(self):
        remote_address = "203.0.113.12"
        for index in range(35):
            response = self.client.post(
                reverse("accounts:login"),
                {
                    "username": f"random-attacker-name-{index}",
                    "password": "wrong-password",
                },
                REMOTE_ADDR=remote_address,
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(
            LoginAttempt.objects.filter(scope=LoginAttempt.Scope.ACCOUNT).count(),
            30,
        )
        network_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.NETWORK)
        self.assertEqual(network_attempt.failures, 30)
        self.assertIsNotNone(network_attempt.locked_until)
        self.assertEqual(LoginAttempt.objects.count(), 31)

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_primed_real_and_unknown_failures_share_status_and_query_path(self):
        self.user.set_password(PASSWORD)
        self.user.save(update_fields=("password",))

        def capture_failure(username, remote_address):
            cache.clear()
            LoginAttempt.objects.all().delete()
            client = Client()
            for index in range(5):
                prime_response = client.post(
                    reverse("accounts:login"),
                    {
                        "username": f"prime-{index}",
                        "password": "wrong-password",
                    },
                    REMOTE_ADDR=remote_address,
                )
                self.assertEqual(prime_response.status_code, 200)

            with CaptureQueriesContext(connection) as queries:
                response = client.post(
                    reverse("accounts:login"),
                    {"username": username, "password": "wrong-password"},
                    REMOTE_ADDR=remote_address,
                )
            operation_path = tuple(
                query["sql"].lstrip().split(maxsplit=1)[0].upper()
                for query in queries.captured_queries
            )
            return response.status_code, len(queries), operation_path

        existing_result = capture_failure("alice", "203.0.113.16")
        unknown_result = capture_failure("no-such-account", "203.0.113.17")

        self.assertEqual(existing_result, unknown_result)

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
    def test_real_and_unknown_candidate_lockouts_allow_same_network_owner_login(self):
        self.user.set_password(PASSWORD)
        self.user.save(update_fields=("password",))
        outcomes = []

        scenarios = (
            ("real", self.user.username, "203.0.113.18"),
            ("unknown", "no-such-candidate", "203.0.113.19"),
        )
        for label, candidate, remote_address in scenarios:
            with self.subTest(candidate_kind=label):
                cache.clear()
                LoginAttempt.objects.all().delete()
                owner = get_user_model().objects.create_user(
                    username=f"owner-{label}",
                    password=PASSWORD,
                )
                client = Client()

                for _index in range(30):
                    failure_response = client.post(
                        reverse("accounts:login"),
                        {"username": candidate, "password": "wrong-password"},
                        REMOTE_ADDR=remote_address,
                    )
                    self.assertEqual(failure_response.status_code, 200)

                success_response = client.post(
                    reverse("accounts:login"),
                    {"username": owner.username, "password": PASSWORD},
                    REMOTE_ADDR=remote_address,
                )

                self.assertRedirects(success_response, reverse("market:home"))
                self.assertEqual(int(client.session["_auth_user_id"]), owner.pk)
                network_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.NETWORK)
                outcomes.append(
                    (
                        success_response.status_code,
                        success_response.url,
                        network_attempt.failures,
                    )
                )

        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[0], (302, reverse("market:home"), 6))

    def test_expired_login_attempt_cleanup_removes_only_safe_stale_rows(self):
        now = timezone.now()
        stale_time = now - LOGIN_ATTEMPT_RETENTION - timedelta(seconds=1)
        expired_unlocked = LoginAttempt.objects.create(
            scope=LoginAttempt.Scope.ACCOUNT,
            key_hash="a" * 64,
            failures=1,
            window_started=stale_time,
        )
        expired_lock = LoginAttempt.objects.create(
            scope=LoginAttempt.Scope.ACCOUNT,
            key_hash="b" * 64,
            failures=5,
            window_started=stale_time,
            locked_until=now - timedelta(seconds=1),
        )
        active_lock = LoginAttempt.objects.create(
            scope=LoginAttempt.Scope.ACCOUNT,
            key_hash="c" * 64,
            failures=5,
            window_started=stale_time,
            locked_until=now + timedelta(minutes=1),
        )
        recent = LoginAttempt.objects.create(
            scope=LoginAttempt.Scope.NETWORK,
            key_hash="d" * 64,
            failures=1,
            window_started=now,
        )

        cache.clear()
        _purge_expired_login_attempts(now)

        remaining_ids = set(LoginAttempt.objects.values_list("pk", flat=True))
        self.assertNotIn(expired_unlocked.pk, remaining_ids)
        self.assertNotIn(expired_lock.pk, remaining_ids)
        self.assertIn(active_lock.pk, remaining_ids)
        self.assertIn(recent.pk, remaining_ids)

    def test_oversized_username_is_rejected_without_authentication_work(self):
        oversized_username = "a" * 151

        with self.assertLogs("tiny_market.security", level="WARNING"):
            response = self.client.post(
                reverse("accounts:login"),
                {"username": oversized_username, "password": PASSWORD},
                REMOTE_ADDR="203.0.113.13",
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response.context["form"].is_bound)
        self.assertEqual(response.context["form"].data["username"], "")
        self.assertEqual(response.context["form"].data["password"], "")
        self.assertNotContains(response, oversized_username)

    def test_oversized_password_is_rejected_without_validating_login_form(self):
        oversized_password = "x" * 257

        original_is_valid = LoginForm.is_valid
        validated_passwords = []

        def recording_is_valid(form):
            validated_passwords.append(form.data.get("password"))
            return original_is_valid(form)

        # The input-size gate must run before AuthenticationForm validation.
        with patch.object(LoginForm, "is_valid", recording_is_valid):
            response = self.client.post(
                reverse("accounts:login"),
                {"username": "alice", "password": oversized_password},
                REMOTE_ADDR="203.0.113.14",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(validated_passwords, [""])
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response.context["form"].is_bound)
        self.assertEqual(response.context["form"].data["username"], "alice")
        self.assertEqual(response.context["form"].data["password"], "")

    def test_suspended_user_cannot_login(self):
        self.user.is_suspended = True
        self.user.is_active = False
        self.user.save(update_fields=("is_suspended", "is_active"))

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": PASSWORD},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_is_post_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("market:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("accounts:login"),
            {"username": "alice", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 403)

    def test_untrusted_peer_cannot_spoof_forwarded_network_address(self):
        request = RequestFactory().get(
            "/accounts/login/",
            REMOTE_ADDR="198.51.100.10",
            HTTP_X_FORWARDED_FOR="203.0.113.99",
        )

        self.assertEqual(_network_identifier(request), "198.51.100.10")

    @override_settings(TRUSTED_PROXY_IPS=frozenset({"198.51.100.10"}))
    def test_trusted_proxy_can_supply_valid_client_address(self):
        request = RequestFactory().get(
            "/accounts/login/",
            REMOTE_ADDR="198.51.100.10",
            HTTP_X_FORWARDED_FOR="203.0.113.99, 198.51.100.10",
        )

        self.assertEqual(_network_identifier(request), "203.0.113.99")


class AdminLoginSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = get_user_model().objects.create_superuser(
            username="admin",
            password=PASSWORD,
        )

    def test_admin_login_uses_account_and_network_throttling(self):
        for _index in range(5):
            response = self.client.post(
                reverse("admin:login"),
                {"username": "admin", "password": "wrong-password"},
                REMOTE_ADDR="203.0.113.60",
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse("admin:login"),
            {"username": "admin", "password": PASSWORD},
            REMOTE_ADDR="203.0.113.60",
        )

        self.assertEqual(response.status_code, 429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_successful_admin_login_clears_only_account_attempt(self):
        self.client.post(
            reverse("admin:login"),
            {"username": "admin", "password": "wrong-password"},
            REMOTE_ADDR="203.0.113.61",
        )
        self.assertTrue(LoginAttempt.objects.exists())

        response = self.client.post(
            reverse("admin:login"),
            {"username": "admin", "password": PASSWORD},
            REMOTE_ADDR="203.0.113.61",
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(LoginAttempt.objects.filter(scope=LoginAttempt.Scope.ACCOUNT).exists())
        network_attempt = LoginAttempt.objects.get(scope=LoginAttempt.Scope.NETWORK)
        self.assertEqual(network_attempt.failures, 2)

    def test_authenticated_staff_post_cannot_clear_another_users_lock_records(self):
        victim = get_user_model().objects.create_user(
            username="victim",
            password=PASSWORD,
        )
        remote_address = "203.0.113.62"
        for _index in range(5):
            self.client.post(
                reverse("accounts:login"),
                {"username": victim.username, "password": "wrong-password"},
                REMOTE_ADDR=remote_address,
            )

        locked_records = {
            record.pk: (record.failures, record.locked_until)
            for record in LoginAttempt.objects.all()
        }
        self.assertTrue(locked_records)
        self.assertTrue(any(locked_until for _, locked_until in locked_records.values()))

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:login"),
            {"username": victim.username, "password": PASSWORD},
            REMOTE_ADDR=remote_address,
        )

        self.assertRedirects(response, reverse("admin:index"))
        self.assertEqual(
            {
                record.pk: (record.failures, record.locked_until)
                for record in LoginAttempt.objects.all()
            },
            locked_records,
        )

    def test_authenticated_nonstaff_cannot_post_to_admin_login(self):
        ordinary = get_user_model().objects.create_user(
            username="ordinary-admin-login",
            password=PASSWORD,
        )
        self.client.force_login(ordinary)

        response = self.client.post(
            reverse("admin:login"),
            {"username": self.admin.username, "password": PASSWORD},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(int(self.client.session["_auth_user_id"]), ordinary.pk)

    def test_oversized_admin_credentials_are_rejected_before_admin_authentication(self):
        payloads = (
            {"username": "a" * 151, "password": PASSWORD},
            {"username": self.admin.username, "password": "x" * 257},
        )
        for index, payload in enumerate(payloads):
            with self.subTest(payload_index=index):
                cache.clear()
                LoginAttempt.objects.all().delete()
                with patch.object(admin.site, "login") as admin_login:
                    response = self.client.post(
                        reverse("admin:login"),
                        payload,
                        REMOTE_ADDR=f"203.0.113.{70 + index}",
                    )

                self.assertEqual(response.status_code, 400)
                admin_login.assert_not_called()
                self.assertNotIn("_auth_user_id", self.client.session)


class UserSuspensionInvariantTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice-invariant",
            password=PASSWORD,
        )

    def test_clean_and_save_force_suspended_user_inactive(self):
        self.user.is_suspended = True
        self.user.is_active = True
        self.user.clean()
        self.assertFalse(self.user.is_active)

        # Reset the invalid value to exercise save() independently of clean().
        self.user.is_active = True
        self.user.save(update_fields=("is_suspended", "is_active"))
        self.user.refresh_from_db()

        self.assertTrue(self.user.is_suspended)
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.suspended_at)

    def test_database_rejects_suspended_active_bulk_update(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                get_user_model().objects.filter(pk=self.user.pk).update(
                    is_suspended=True,
                    is_active=True,
                )


class ReadOnlySecurityRecordAdminTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.root = user_model.objects.create_superuser(
            username="readonly-root",
            password=PASSWORD,
        )
        self.blocker = user_model.objects.create_user(
            username="readonly-blocker",
            password=PASSWORD,
        )
        self.blocked = user_model.objects.create_user(
            username="readonly-blocked",
            password=PASSWORD,
        )
        self.user_block = UserBlock.objects.create(
            blocker=self.blocker,
            blocked=self.blocked,
        )
        self.login_attempt = LoginAttempt.objects.create(
            scope=LoginAttempt.Scope.ACCOUNT,
            key_hash="e" * 64,
            failures=1,
        )
        self.user_block_admin = UserBlockAdmin(UserBlock, admin.site)
        self.login_attempt_admin = LoginAttemptAdmin(LoginAttempt, admin.site)
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get("/admin/accounts/")
        request.user = self.root
        return request

    def test_all_concrete_fields_are_readonly_and_mutation_permissions_are_denied(self):
        request = self._request()
        admin_objects = (
            (self.user_block_admin, UserBlock, self.user_block),
            (self.login_attempt_admin, LoginAttempt, self.login_attempt),
        )

        for model_admin, model, instance in admin_objects:
            with self.subTest(model=model._meta.label):
                expected_fields = {field.name for field in model._meta.concrete_fields}
                self.assertEqual(
                    set(model_admin.get_readonly_fields(request, instance)),
                    expected_fields,
                )
                self.assertTrue(model_admin.has_view_permission(request, instance))
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request, instance))
                self.assertFalse(model_admin.has_delete_permission(request, instance))

    def test_forged_change_posts_cannot_mutate_security_records(self):
        block_snapshot = (
            self.user_block.blocker_id,
            self.user_block.blocked_id,
            self.user_block.created_at,
        )
        attempt_snapshot = (
            self.login_attempt.scope,
            self.login_attempt.key_hash,
            self.login_attempt.failures,
            self.login_attempt.window_started,
            self.login_attempt.locked_until,
        )
        self.client.force_login(self.root)

        block_response = self.client.post(
            reverse(
                "admin:accounts_userblock_change",
                args=[self.user_block.pk],
            ),
            {
                "blocker": self.blocked.pk,
                "blocked": self.blocker.pk,
                "_save": "Save",
            },
        )
        attempt_response = self.client.post(
            reverse(
                "admin:accounts_loginattempt_change",
                args=[self.login_attempt.pk],
            ),
            {
                "scope": LoginAttempt.Scope.NETWORK,
                "key_hash": "f" * 64,
                "failures": 99,
                "_save": "Save",
            },
        )

        self.assertEqual(block_response.status_code, 403)
        self.assertEqual(attempt_response.status_code, 403)
        self.user_block.refresh_from_db()
        self.login_attempt.refresh_from_db()
        self.assertEqual(
            (
                self.user_block.blocker_id,
                self.user_block.blocked_id,
                self.user_block.created_at,
            ),
            block_snapshot,
        )
        self.assertEqual(
            (
                self.login_attempt.scope,
                self.login_attempt.key_hash,
                self.login_attempt.failures,
                self.login_attempt.window_started,
                self.login_attempt.locked_until,
            ),
            attempt_snapshot,
        )

    def test_forged_delete_posts_cannot_remove_security_records(self):
        self.client.force_login(self.root)

        block_response = self.client.post(
            reverse(
                "admin:accounts_userblock_delete",
                args=[self.user_block.pk],
            ),
            {"post": "yes"},
        )
        attempt_response = self.client.post(
            reverse(
                "admin:accounts_loginattempt_delete",
                args=[self.login_attempt.pk],
            ),
            {"post": "yes"},
        )

        self.assertEqual(block_response.status_code, 403)
        self.assertEqual(attempt_response.status_code, 403)
        self.assertTrue(UserBlock.objects.filter(pk=self.user_block.pk).exists())
        self.assertTrue(LoginAttempt.objects.filter(pk=self.login_attempt.pk).exists())


class UserAdminSuspensionActionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.actor = user_model.objects.create_superuser(
            username="root-admin",
            password=PASSWORD,
        )
        self.ordinary = user_model.objects.create_user(
            username="ordinary",
            password=PASSWORD,
        )
        self.staff_target = user_model.objects.create_user(
            username="staff-target",
            password=PASSWORD,
            is_staff=True,
        )
        self.superuser_target = user_model.objects.create_superuser(
            username="other-root",
            password=PASSWORD,
        )
        self.model_admin = UserAdmin(user_model, admin.site)
        self.factory = RequestFactory()

    def _request_for(self, user):
        request = self.factory.post("/admin/accounts/user/")
        request.user = user
        return request

    def test_bulk_suspend_only_changes_ordinary_accounts(self):
        self.model_admin.suspend_selected(
            self._request_for(self.actor),
            get_user_model().objects.all(),
        )

        for user in (
            self.actor,
            self.ordinary,
            self.staff_target,
            self.superuser_target,
        ):
            user.refresh_from_db()

        self.assertTrue(self.ordinary.is_suspended)
        self.assertFalse(self.ordinary.is_active)
        for protected in (self.actor, self.staff_target, self.superuser_target):
            self.assertFalse(protected.is_suspended)
            self.assertTrue(protected.is_active)

    def test_direct_action_call_requires_dedicated_suspend_permission(self):
        limited_staff = get_user_model().objects.create_user(
            username="limited-staff",
            password=PASSWORD,
            is_staff=True,
        )

        with self.assertRaises(PermissionDenied):
            self.model_admin.suspend_selected(
                self._request_for(limited_staff),
                get_user_model().objects.filter(pk=self.ordinary.pk),
            )

        self.ordinary.refresh_from_db()
        self.assertFalse(self.ordinary.is_suspended)
        self.assertTrue(self.ordinary.is_active)


class UserAdminPrivilegeBoundaryTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.limited_staff = user_model.objects.create_user(
            username="account-editor",
            password=PASSWORD,
            is_staff=True,
        )
        self.ordinary = user_model.objects.create_user(
            username="editable-user",
            password=PASSWORD,
        )
        self.staff_target = user_model.objects.create_user(
            username="protected-staff",
            password=PASSWORD,
            is_staff=True,
        )
        self.superuser_target = user_model.objects.create_superuser(
            username="protected-root",
            password=PASSWORD,
        )
        self.change_permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="change_user",
        )
        self.delete_permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="delete_user",
        )
        self.view_permission = Permission.objects.get(
            content_type__app_label="accounts",
            codename="view_user",
        )
        self.limited_staff.user_permissions.add(
            self.change_permission,
            self.delete_permission,
            self.view_permission,
        )
        self.model_admin = UserAdmin(user_model, admin.site)
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.get("/admin/accounts/user/")
        request.user = self.limited_staff
        return request

    def test_non_superuser_sees_privilege_and_account_state_as_readonly(self):
        readonly_fields = set(self.model_admin.get_readonly_fields(self._request(), self.ordinary))

        self.assertTrue(set(self.model_admin.privilege_fields) <= readonly_fields)
        self.assertTrue(set(self.model_admin.account_state_fields) <= readonly_fields)

    def test_non_superuser_cannot_change_or_delete_protected_accounts(self):
        request = self._request()

        self.assertTrue(self.model_admin.has_change_permission(request, self.ordinary))
        self.assertTrue(self.model_admin.has_delete_permission(request, self.ordinary))
        for protected in (self.limited_staff, self.staff_target, self.superuser_target):
            self.assertFalse(self.model_admin.has_change_permission(request, protected))
            self.assertFalse(self.model_admin.has_delete_permission(request, protected))

    def test_forged_admin_post_cannot_escalate_ordinary_user_privileges(self):
        target_permission = Permission.objects.get(
            content_type__app_label="auth",
            codename="add_group",
        )
        self.client.force_login(self.limited_staff)

        response = self.client.post(
            reverse("admin:accounts_user_change", args=[self.ordinary.pk]),
            {
                "username": self.ordinary.username,
                "password": self.ordinary.password,
                "first_name": "Edited",
                "last_name": "User",
                "email": "edited@example.test",
                "is_active": "on",
                "is_staff": "on",
                "is_superuser": "on",
                "is_suspended": "on",
                "suspension_reason": "forged suspension state",
                "groups": [],
                "user_permissions": [target_permission.pk],
                "_save": "Save",
            },
        )

        self.assertRedirects(response, reverse("admin:accounts_user_changelist"))
        self.ordinary.refresh_from_db()
        self.assertEqual(self.ordinary.first_name, "Edited")
        self.assertFalse(self.ordinary.is_staff)
        self.assertFalse(self.ordinary.is_superuser)
        self.assertFalse(self.ordinary.is_suspended)
        self.assertTrue(self.ordinary.is_active)
        self.assertFalse(self.ordinary.groups.exists())
        self.assertFalse(self.ordinary.user_permissions.exists())

    def test_forged_admin_post_to_protected_account_is_denied(self):
        self.client.force_login(self.limited_staff)

        for protected in (self.staff_target, self.superuser_target):
            response = self.client.post(
                reverse("admin:accounts_user_change", args=[protected.pk]),
                {
                    "username": protected.username,
                    "password": protected.password,
                    "first_name": "Compromised",
                    "_save": "Save",
                },
            )
            self.assertEqual(response.status_code, 403)

        self.staff_target.refresh_from_db()
        self.superuser_target.refresh_from_db()
        self.assertEqual(self.staff_target.first_name, "")
        self.assertEqual(self.superuser_target.first_name, "")

    def test_non_superuser_cannot_post_to_user_password_change_endpoint(self):
        original_password_hash = self.ordinary.password
        self.client.force_login(self.limited_staff)

        response = self.client.post(
            reverse(
                "admin:auth_user_password_change",
                args=[self.ordinary.pk],
            ),
            {
                "usable_password": "true",
                "password1": NEW_PASSWORD,
                "password2": NEW_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 403)
        self.ordinary.refresh_from_db()
        self.assertEqual(self.ordinary.password, original_password_hash)
        self.assertTrue(self.ordinary.check_password(PASSWORD))
        self.assertFalse(self.ordinary.check_password(NEW_PASSWORD))

    def test_superuser_can_reset_password_and_new_password_authenticates(self):
        self.client.force_login(self.superuser_target)

        response = self.client.post(
            reverse(
                "admin:auth_user_password_change",
                args=[self.ordinary.pk],
            ),
            {
                "usable_password": "true",
                "password1": NEW_PASSWORD,
                "password2": NEW_PASSWORD,
            },
        )

        self.assertRedirects(
            response,
            reverse("admin:accounts_user_change", args=[self.ordinary.pk]),
        )
        self.ordinary.refresh_from_db()
        self.assertTrue(self.ordinary.check_password(NEW_PASSWORD))
        self.assertFalse(self.ordinary.check_password(PASSWORD))

        self.client.logout()
        cache.clear()
        LoginAttempt.objects.all().delete()
        login_response = self.client.post(
            reverse("accounts:login"),
            {"username": self.ordinary.username, "password": NEW_PASSWORD},
            REMOTE_ADDR="203.0.113.80",
        )

        self.assertRedirects(login_response, reverse("market:home"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.ordinary.pk,
        )


class PublicProfileSecurityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="alice",
            password=PASSWORD,
            email="private-email-token@example.invalid",
            bio="안전한 거래를 좋아합니다.",
        )

    def test_active_ordinary_profile_is_public_and_allowlisted(self):
        get_user_model().objects.filter(pk=self.user.pk).update(
            suspension_reason="private-suspension-token",
        )

        response = self.client.get(
            reverse("accounts:public_profile", args=["ALICE"]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["profile"],
            {
                "username": "alice",
                "bio": "안전한 거래를 좋아합니다.",
            },
        )
        self.assertContains(response, "alice")
        self.assertContains(response, "안전한 거래를 좋아합니다.")
        self.assertNotContains(response, "private-email-token")
        self.assertNotContains(response, "private-suspension-token")
        self.assertNotContains(response, "is_staff")
        self.assertNotContains(response, "is_superuser")
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_profile_bio_is_html_escaped(self):
        self.user.bio = '<script>alert("profile-xss")</script>\n다음 줄'
        self.user.save(update_fields=("bio",))

        response = self.client.get(
            reverse("accounts:public_profile", args=[self.user.username]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>")
        self.assertContains(response, "&lt;script&gt;")
        self.assertContains(response, "다음 줄")

    def test_unavailable_and_privileged_accounts_have_no_public_profile(self):
        inactive = get_user_model().objects.create_user(
            username="inactive",
            password=PASSWORD,
            is_active=False,
        )
        suspended = get_user_model().objects.create_user(
            username="suspended",
            password=PASSWORD,
        )
        suspended.is_suspended = True
        suspended.suspension_reason = "private reason"
        suspended.save(update_fields=("is_suspended", "suspension_reason"))
        staff = get_user_model().objects.create_user(
            username="staff",
            password=PASSWORD,
            is_staff=True,
        )
        superuser = get_user_model().objects.create_superuser(
            username="root",
            password=PASSWORD,
        )

        for hidden_user in (inactive, suspended, staff, superuser):
            with self.subTest(username=hidden_user.username):
                response = self.client.get(
                    reverse(
                        "accounts:public_profile",
                        args=[hidden_user.username],
                    ),
                )
                self.assertEqual(response.status_code, 404)

    def test_public_profile_is_read_only(self):
        response = self.client.post(
            reverse("accounts:public_profile", args=[self.user.username]),
            {"bio": "forged"},
        )

        self.assertEqual(response.status_code, 405)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "안전한 거래를 좋아합니다.")


class MyPageSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="alice",
            password=PASSWORD,
            email="original@example.invalid",
            bio="기존 소개글",
        )
        self.client.force_login(self.user)

    def test_mypage_requires_authentication_and_is_not_cached(self):
        response = self.client.get(reverse("accounts:mypage"))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context["profile_form"], ProfileForm)
        self.assertIn("no-store", response.headers["Cache-Control"])

        self.client.logout()
        response = self.client.get(reverse("accounts:mypage"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:mypage')}",
        )

    def test_profile_update_uses_an_explicit_field_allowlist(self):
        response = self.client.post(
            reverse("accounts:mypage"),
            {
                "bio": "변경된 소개글",
                "username": "attacker-controlled",
                "email": "attacker@example.invalid",
                "is_active": "",
                "is_staff": "on",
                "is_superuser": "on",
                "is_suspended": "on",
                "suspension_reason": "forged reason",
            },
        )

        self.assertRedirects(response, reverse("accounts:mypage"))
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "변경된 소개글")
        self.assertEqual(self.user.username, "alice")
        self.assertEqual(self.user.email, "original@example.invalid")
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_suspended)
        self.assertEqual(self.user.suspension_reason, "")

    def test_profile_update_rejects_more_than_500_characters(self):
        response = self.client.post(
            reverse("accounts:mypage"),
            {"bio": "가" * 501},
        )

        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context["profile_form"].errors)
        self.user.refresh_from_db()
        self.assertEqual(self.user.bio, "기존 소개글")

    def test_password_change_requires_the_current_password(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": "wrong-current-password",
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))
        self.assertFalse(self.user.check_password(NEW_PASSWORD))

    def test_password_change_applies_configured_strength_validators(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": "short",
                "new_password2": "short",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_change_rejects_oversized_input_before_hashing(self):
        with patch("accounts.views.PasswordChangeForm.is_valid") as is_valid:
            response = self.client.post(
                reverse("accounts:password_change"),
                {
                    "old_password": "x" * 257,
                    "new_password1": NEW_PASSWORD,
                    "new_password2": NEW_PASSWORD,
                },
            )

        self.assertEqual(response.status_code, 400)
        is_valid.assert_not_called()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_password_change_is_rate_limited_before_form_validation(self):
        post_data = {
            "old_password": "wrong-current-password",
            "new_password1": NEW_PASSWORD,
            "new_password2": NEW_PASSWORD,
        }
        with patch(
            "accounts.views.PasswordChangeForm.is_valid",
            return_value=False,
        ) as is_valid:
            for _index in range(10):
                response = self.client.post(
                    reverse("accounts:password_change"),
                    post_data,
                )
                self.assertEqual(response.status_code, 400)

            response = self.client.post(
                reverse("accounts:password_change"),
                post_data,
            )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers["Retry-After"], "3600")
        self.assertEqual(is_valid.call_count, 10)

    def test_successful_password_change_preserves_authenticated_session(self):
        old_session_key = self.client.session.session_key

        response = self.client.post(
            reverse("accounts:password_change"),
            {
                "old_password": PASSWORD,
                "new_password1": NEW_PASSWORD,
                "new_password2": NEW_PASSWORD,
            },
        )

        self.assertRedirects(response, reverse("accounts:mypage"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.user.pk,
        )
        self.assertNotEqual(self.client.session.session_key, old_session_key)
        self.assertEqual(
            self.client.get(reverse("accounts:mypage")).status_code,
            200,
        )

    def test_password_endpoint_rejects_get(self):
        response = self.client.get(reverse("accounts:password_change"))

        self.assertEqual(response.status_code, 405)

    def test_account_that_becomes_suspended_cannot_use_mypage(self):
        self.user.is_suspended = True
        self.user.suspension_reason = "policy violation"
        self.user.save(update_fields=("is_suspended", "suspension_reason"))

        response = self.client.get(reverse("accounts:mypage"))

        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('accounts:mypage')}",
        )
