from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.properties.models import Property

DEMO_USERS = ["admin_demo", "host_asha", "host_ravi", "guest_meera", "guest_karan"]


class SeedDemoTests(TestCase):
    def run_seed(self):
        call_command("seed_demo", "--no-images", "--force", stdout=StringIO(), stderr=StringIO())

    def test_creates_users_and_properties(self):
        self.run_seed()
        User = get_user_model()
        self.assertEqual(User.objects.filter(username__in=DEMO_USERS).count(), 5)
        self.assertEqual(User.objects.get(username="admin_demo").role, "admin")
        self.assertEqual(User.objects.get(username="host_asha").role, "host")
        self.assertEqual(Property.objects.filter(host__username__in=["host_asha", "host_ravi"]).count(), 6)

    def test_is_idempotent(self):
        self.run_seed()
        users, props = get_user_count(), Property.objects.count()
        self.run_seed()
        self.assertEqual(get_user_count(), users)
        self.assertEqual(Property.objects.count(), props)

    def test_refuses_without_debug(self):
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("seed_demo", "--no-images", stdout=StringIO(), stderr=StringIO())


def get_user_count():
    return get_user_model().objects.count()