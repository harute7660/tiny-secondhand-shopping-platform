from pathlib import Path
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from accounts.models import UserBlock

from .admin import GlobalChatMessageAdmin
from .models import GlobalChatMessage
from .views import _encode_cursor

User = get_user_model()


class GlobalChatSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        self.alice = User.objects.create_user(username="alice")
        self.bob = User.objects.create_user(username="bob")
        self.eve = User.objects.create_user(username="eve")
        self.page_url = reverse("community:global_chat")
        self.api_url = reverse("community:global_chat_messages")
        self.send_url = reverse("community:global_chat_send")

    def tearDown(self):
        cache.clear()

    def login(self, user=None):
        self.client.force_login(user or self.alice)

    def test_all_endpoints_require_authentication_and_suspension_uses_existing_auth_gate(self):
        self.assertEqual(self.client.get(self.page_url).status_code, 302)
        self.assertEqual(
            self.client.get(self.api_url, {"cursor": _encode_cursor(0)}).status_code,
            302,
        )
        self.assertEqual(self.client.post(self.send_url, {"body": "hello"}).status_code, 302)

        suspended = User.objects.create_user(
            username="suspended",
            is_active=False,
            is_suspended=True,
        )
        self.client.force_login(suspended)
        self.assertEqual(self.client.get(self.page_url).status_code, 302)
        self.assertEqual(GlobalChatMessage.objects.count(), 0)

    def test_send_requires_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.alice)

        response = csrf_client.post(self.send_url, {"body": "csrf missing"})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(GlobalChatMessage.objects.exists())

    def test_sender_is_derived_from_session_and_client_sender_is_ignored(self):
        self.login()

        response = self.client.post(
            self.send_url,
            {"body": "server chooses sender", "sender": str(self.bob.pk)},
        )

        self.assertEqual(response.status_code, 302)
        message = GlobalChatMessage.objects.get()
        self.assertEqual(message.sender, self.alice)
        self.assertNotEqual(message.sender, self.bob)

    def test_xss_is_escaped_in_html_and_polling_uses_text_content(self):
        body = '<script>alert("x")</script><img src=x onerror=alert(1)>'
        GlobalChatMessage.objects.create(sender=self.bob, body=body)
        self.login()

        page_response = self.client.get(self.page_url)
        api_response = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "limit": 10},
        )

        self.assertEqual(page_response.status_code, 200)
        self.assertContains(page_response, "&lt;script&gt;alert")
        self.assertNotContains(page_response, '<script>alert("x")</script>')
        self.assertContains(page_response, 'aria-live="polite"')
        self.assertEqual(api_response.json()["messages"][0]["body"], body)

        js_source = (
            Path(__file__).resolve().parent.parent / "static" / "js" / "global_chat.js"
        ).read_text(encoding="utf-8")
        self.assertIn("textContent", js_source)
        self.assertNotIn("innerHTML", js_source)
        self.assertIn("MAX_RENDERED_MESSAGES = 200", js_source)
        self.assertIn("rows[index].remove()", js_source)

    def test_empty_and_oversized_bodies_are_rejected(self):
        self.login()

        empty_response = self.client.post(self.send_url, {"body": "   "})
        oversized_response = self.client.post(self.send_url, {"body": "x" * 1_001})

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(oversized_response.status_code, 400)
        self.assertEqual(GlobalChatMessage.objects.count(), 0)

    def test_oversized_body_is_rejected_before_form_construction(self):
        self.login()

        with patch("community.views.GlobalChatMessageForm") as form_class:
            response = self.client.post(self.send_url, {"body": "x" * 1_001})

        self.assertEqual(response.status_code, 400)
        form_class.assert_not_called()
        self.assertFalse(GlobalChatMessage.objects.exists())

    def test_send_rate_is_reserved_before_form_construction_and_validation(self):
        self.login()

        with (
            patch("community.views._consume_user_limit", return_value=False),
            patch("community.views.GlobalChatMessageForm") as form_class,
        ):
            response = self.client.post(self.send_url, {"body": "bounded message"})

        self.assertEqual(response.status_code, 429)
        form_class.assert_not_called()
        self.assertFalse(GlobalChatMessage.objects.exists())

    def test_signed_cursor_pages_incrementally_and_rejects_tampering(self):
        messages = [
            GlobalChatMessage.objects.create(sender=self.bob, body=f"message {index}")
            for index in range(3)
        ]
        self.login()

        first = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "limit": 2},
        )
        first_payload = first.json()
        second = self.client.get(
            self.api_url,
            {"cursor": first_payload["next_cursor"], "limit": 2},
        )
        second_payload = second.json()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(
            [item["id"] for item in first_payload["messages"]],
            [messages[0].pk, messages[1].pk],
        )
        self.assertTrue(first_payload["has_more"])
        self.assertEqual(
            [item["id"] for item in second_payload["messages"]],
            [messages[2].pk],
        )
        self.assertFalse(second_payload["has_more"])

        tampered = self.client.get(
            self.api_url,
            {"cursor": first_payload["next_cursor"] + "x", "limit": 2},
        )
        too_large = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "limit": 101},
        )
        unexpected_filter = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "sender": self.bob.pk},
        )
        self.assertEqual(tampered.status_code, 400)
        self.assertEqual(too_large.status_code, 400)
        self.assertEqual(unexpected_filter.status_code, 400)

    def test_block_relations_hide_messages_in_both_directions(self):
        own = GlobalChatMessage.objects.create(sender=self.alice, body="own visible")
        GlobalChatMessage.objects.create(sender=self.bob, body="outbound hidden")
        GlobalChatMessage.objects.create(sender=self.eve, body="inbound hidden")
        UserBlock.objects.create(blocker=self.alice, blocked=self.bob)
        UserBlock.objects.create(blocker=self.eve, blocked=self.alice)
        self.login()

        api_response = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "limit": 10},
        )
        page_response = self.client.get(self.page_url)

        self.assertEqual(
            [item["id"] for item in api_response.json()["messages"]],
            [own.pk],
        )
        self.assertContains(page_response, "own visible")
        self.assertNotContains(page_response, "outbound hidden")
        self.assertNotContains(page_response, "inbound hidden")

    def test_send_and_poll_are_rate_limited_with_retry_after(self):
        self.login()

        with patch("community.views.SEND_RATE_LIMIT", 2):
            self.assertEqual(
                self.client.post(self.send_url, {"body": "first"}).status_code,
                302,
            )
            self.assertEqual(
                self.client.post(self.send_url, {"body": "second"}).status_code,
                302,
            )
            send_limited = self.client.post(self.send_url, {"body": "third"})

        self.assertEqual(send_limited.status_code, 429)
        self.assertEqual(send_limited.headers["Retry-After"], "60")
        self.assertEqual(GlobalChatMessage.objects.count(), 2)

        cache.clear()
        poll_query = {"cursor": _encode_cursor(0), "limit": 10}
        with patch("community.views.POLL_RATE_LIMIT", 2):
            self.assertEqual(self.client.get(self.api_url, poll_query).status_code, 200)
            self.assertEqual(self.client.get(self.api_url, poll_query).status_code, 200)
            poll_limited = self.client.get(self.api_url, poll_query)

        self.assertEqual(poll_limited.status_code, 429)
        self.assertEqual(poll_limited.headers["Retry-After"], "60")

    def test_private_responses_and_json_minimize_identity_data(self):
        GlobalChatMessage.objects.create(sender=self.bob, body="visible")
        self.login()

        page_response = self.client.get(self.page_url)
        api_response = self.client.get(
            self.api_url,
            {"cursor": _encode_cursor(0), "limit": 10},
        )

        self.assertIn("no-store", page_response.headers["Cache-Control"])
        self.assertIn("no-store", api_response.headers["Cache-Control"])
        message_payload = api_response.json()["messages"][0]
        self.assertEqual(
            set(message_payload),
            {"id", "sender", "body", "created_at", "display_time", "is_own"},
        )
        self.assertNotIn("sender_id", message_payload)


class GlobalChatAdminTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="chat-admin",
            password="A-strong-admin-password-2026",
        )
        self.sender = User.objects.create_user(username="sender")
        self.message = GlobalChatMessage.objects.create(
            sender=self.sender,
            body="preserved chat evidence",
        )
        self.client.force_login(self.superuser)

    def test_admin_changelist_and_detail_are_viewable_but_mutation_is_forbidden(self):
        changelist_url = reverse("admin:community_globalchatmessage_changelist")
        add_url = reverse("admin:community_globalchatmessage_add")
        change_url = reverse(
            "admin:community_globalchatmessage_change",
            args=[self.message.pk],
        )
        delete_url = reverse(
            "admin:community_globalchatmessage_delete",
            args=[self.message.pk],
        )

        changelist = self.client.get(changelist_url)
        detail = self.client.get(change_url)
        add = self.client.get(add_url)
        changed = self.client.post(
            change_url,
            {
                "sender": self.superuser.pk,
                "body": "tampered",
                "created_at": "2026-07-13 12:00:00",
            },
        )
        deleted = self.client.get(delete_url)

        self.assertEqual(changelist.status_code, 200)
        self.assertContains(changelist, "preserved chat evidence")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(add.status_code, 403)
        self.assertEqual(changed.status_code, 403)
        self.assertEqual(deleted.status_code, 403)
        self.message.refresh_from_db()
        self.assertEqual(self.message.sender, self.sender)
        self.assertEqual(self.message.body, "preserved chat evidence")

    def test_admin_has_no_add_change_delete_or_bulk_delete_capability(self):
        model_admin = admin.site._registry[GlobalChatMessage]
        self.assertIsInstance(model_admin, GlobalChatMessageAdmin)
        request = RequestFactory().get("/admin/community/globalchatmessage/")
        request.user = self.superuser

        self.assertFalse(model_admin.has_add_permission(request))
        self.assertFalse(model_admin.has_change_permission(request, self.message))
        self.assertFalse(model_admin.has_delete_permission(request, self.message))
        self.assertNotIn("delete_selected", model_admin.get_actions(request))
        self.assertEqual(
            set(model_admin.readonly_fields),
            {"sender", "body", "created_at"},
        )
