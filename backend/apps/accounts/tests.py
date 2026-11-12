from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APIClient

from apps.core.permissions import IsGuest, IsHost, IsOwnerOrAdmin, IsPlatformAdmin

from .models import User

PASSWORD = "StrongPass@123"


def register_payload(**overrides):
    data = {
        "username": "aniket",
        "email": "aniket@example.com",
        "first_name": "Aniket",
        "password": PASSWORD,
        "password2": PASSWORD,
        "role": "guest",
    }
    data.update(overrides)
    return data


class BaseAuthTestCase(TestCase):
    def setUp(self):
        cache.clear()  # throttle counters har test se pehle reset
        self.client = APIClient()

    def create_user(self, username="guest1", email="guest1@example.com", role=User.Role.GUEST):
        return User.objects.create_user(
            username=username, email=email, password=PASSWORD, role=role
        )

    def login(self, identifier, password=PASSWORD):
        return self.client.post(
            reverse("accounts:login"),
            {"username": identifier, "password": password},
            format="json",
        )

    def authenticate(self, user):
        """Login karke Authorization header set karo, login response data return karo."""
        response = self.login(user.username)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data


class RegistrationTests(BaseAuthTestCase):
    def test_register_success_creates_profile_and_returns_tokens(self):
        response = self.client.post(
            reverse("accounts:register"), register_payload(role="host"), format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

        user = User.objects.get(username="aniket")
        self.assertEqual(user.role, "host")
        self.assertTrue(hasattr(user, "profile"))
        self.assertTrue(hasattr(user, "wishlist"))

    def test_cannot_register_as_admin(self):
        response = self.client.post(
            reverse("accounts:register"), register_payload(role="admin"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="aniket").exists())

    def test_password_mismatch_rejected(self):
        response = self.client.post(
            reverse("accounts:register"),
            register_payload(password2="Different@123"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_weak_password_rejected(self):
        response = self.client.post(
            reverse("accounts:register"),
            register_payload(password="12345678", password2="12345678"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_email_is_case_insensitive(self):
        self.create_user(email="aniket@example.com")
        response = self.client.post(
            reverse("accounts:register"),
            register_payload(username="other", email="ANIKET@EXAMPLE.COM"),
            format="json",
        )
        self.assertEqual(response.status_code, 400)


class LoginTests(BaseAuthTestCase):
    def test_login_with_username_and_with_email(self):
        user = self.create_user(role=User.Role.HOST)

        by_username = self.login(user.username)
        self.assertEqual(by_username.status_code, 200)
        self.assertEqual(by_username.data["user"]["role"], "host")

        by_email = self.login(user.email.upper())
        self.assertEqual(by_email.status_code, 200)
        self.assertIn("access", by_email.data)

    def test_wrong_password_returns_401(self):
        user = self.create_user()
        response = self.login(user.username, "WrongPass@123")
        self.assertEqual(response.status_code, 401)


class ProfileTests(BaseAuthTestCase):
    def test_profile_requires_authentication(self):
        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 401)

    def test_get_and_patch_profile_but_role_is_read_only(self):
        user = self.create_user()
        self.authenticate(user)

        response = self.client.get(reverse("accounts:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], user.username)

        response = self.client.patch(
            reverse("accounts:profile"),
            {"city": "Patna", "bio": "Travel lover", "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        user = User.objects.select_related("profile").get(pk=user.pk)
        self.assertEqual(user.profile.city, "Patna")
        self.assertEqual(user.role, "guest")  # role badla nahi


class TokenTests(BaseAuthTestCase):
    def test_refresh_rotates_and_blacklists_old_token(self):
        user = self.create_user()
        tokens = self.authenticate(user)

        first = self.client.post(
            reverse("accounts:token-refresh"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(first.status_code, 200)
        self.assertIn("refresh", first.data)

        reused = self.client.post(
            reverse("accounts:token-refresh"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(reused.status_code, 401)

    def test_logout_blacklists_refresh_token(self):
        user = self.create_user()
        tokens = self.authenticate(user)

        response = self.client.post(
            reverse("accounts:logout"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)

        refresh = self.client.post(
            reverse("accounts:token-refresh"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(refresh.status_code, 401)


class PasswordTests(BaseAuthTestCase):
    def test_forgot_password_existing_and_unknown_email_same_response(self):
        user = self.create_user()

        existing = self.client.post(
            reverse("accounts:password-forgot"), {"email": user.email}, format="json"
        )
        unknown = self.client.post(
            reverse("accounts:password-forgot"), {"email": "nobody@example.com"}, format="json"
        )

        self.assertEqual(existing.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(existing.data, unknown.data)
        self.assertEqual(len(mail.outbox), 1)  # mail sirf existing user ko gayi
        self.assertIn("reset-password?uid=", mail.outbox[0].body)

    def test_reset_password_flow_and_single_use_token(self):
        user = self.create_user()
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
            "new_password": "NewStrong@456",
            "new_password2": "NewStrong@456",
        }

        response = self.client.post(reverse("accounts:password-reset"), payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.login(user.username, "NewStrong@456").status_code, 200)

        # Wahi link dobara use nahi ho sakta
        again = self.client.post(reverse("accounts:password-reset"), payload, format="json")
        self.assertEqual(again.status_code, 400)

    def test_change_password(self):
        user = self.create_user()
        self.authenticate(user)

        wrong = self.client.post(
            reverse("accounts:password-change"),
            {
                "old_password": "WrongOld@123",
                "new_password": "NewStrong@456",
                "new_password2": "NewStrong@456",
            },
            format="json",
        )
        self.assertEqual(wrong.status_code, 400)

        ok = self.client.post(
            reverse("accounts:password-change"),
            {
                "old_password": PASSWORD,
                "new_password": "NewStrong@456",
                "new_password2": "NewStrong@456",
            },
            format="json",
        )
        self.assertEqual(ok.status_code, 200)

        self.client.credentials()  # header hatao
        self.assertEqual(self.login(user.username, "NewStrong@456").status_code, 200)


class FakeRequest:
    def __init__(self, user):
        self.user = user


class PermissionClassTests(SimpleTestCase):
    """Role-based permission classes (DB ki zaroorat nahi)."""

    def test_role_permissions(self):
        guest = User(username="g", role="guest")
        host = User(username="h", role="host")
        admin = User(username="a", role="admin")

        self.assertTrue(IsGuest().has_permission(FakeRequest(guest), None))
        self.assertFalse(IsGuest().has_permission(FakeRequest(host), None))
        self.assertTrue(IsHost().has_permission(FakeRequest(host), None))
        self.assertFalse(IsHost().has_permission(FakeRequest(guest), None))
        self.assertTrue(IsPlatformAdmin().has_permission(FakeRequest(admin), None))
        self.assertFalse(IsPlatformAdmin().has_permission(FakeRequest(host), None))

    def test_owner_or_admin(self):
        owner = User(username="owner", role="host")
        stranger = User(username="stranger", role="host")
        admin = User(username="admin", role="admin")

        class Obj:
            host = owner

        class View:
            owner_field = "host"

        permission = IsOwnerOrAdmin()
        self.assertTrue(permission.has_object_permission(FakeRequest(owner), View(), Obj()))
        self.assertFalse(permission.has_object_permission(FakeRequest(stranger), View(), Obj()))
        self.assertTrue(permission.has_object_permission(FakeRequest(admin), View(), Obj()))