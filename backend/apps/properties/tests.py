import io
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings.models import Booking

from .models import Amenity, Property, PropertyImage

PASSWORD = "StrongPass@123"
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

# Tests hamesha local storage use karein (Cloudinary par kuch upload na ho)
LOCAL_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def list_url():
    return reverse("properties:property-list")


def detail_url(pk):
    return reverse("properties:property-detail", args=[pk])


def my_url():
    return reverse("properties:property-my")


def images_url(pk):
    return reverse("properties:property-upload-images", args=[pk])


def image_detail_url(pk, image_id):
    return reverse("properties:property-manage-image", kwargs={"pk": pk, "image_id": image_id})


def make_user(username, role):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com", password=PASSWORD, role=role
    )


def make_property(host, **overrides):
    data = {
        "host": host,
        "title": "Cozy Beach Villa",
        "description": "Beautiful villa a short walk from the beach.",
        "property_type": "villa",
        "address": "12 Beach Road",
        "city": "Goa",
        "state": "Goa",
        "price_per_night": Decimal("2500.00"),
        "max_guests": 4,
    }
    data.update(overrides)
    return Property.objects.create(**data)


def property_payload(**overrides):
    data = {
        "title": "Cozy Beach Villa",
        "description": "Beautiful villa a short walk from the beach.",
        "property_type": "villa",
        "address": "12 Beach Road",
        "city": "Goa",
        "state": "Goa",
        "price_per_night": "2500.00",
        "max_guests": 4,
        "bedrooms": 2,
        "beds": 3,
        "bathrooms": 2,
    }
    data.update(overrides)
    return data


def make_image(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT, STORAGES=LOCAL_STORAGES)
class PropertyAPITestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = make_user("host1", "host")
        cls.other_host = make_user("host2", "host")
        cls.guest = make_user("guest1", "guest")
        cls.admin = make_user("admin1", "admin")

    def setUp(self):
        self.client = APIClient()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def upload(self, prop, count=2):
        files = [make_image(f"photo{i}.png") for i in range(count)]
        return self.client.post(images_url(prop.pk), {"images": files}, format="multipart")


# ---------------------------------------------------------------------------
# CRUD + permissions
# ---------------------------------------------------------------------------
class PropertyCrudTests(PropertyAPITestCase):
    def test_host_creates_property_with_amenities(self):
        amenity = Amenity.objects.create(name="Wi-Fi", icon="FaWifi")
        self.client.force_authenticate(self.host)

        response = self.client.post(
            list_url(), property_payload(amenity_ids=[amenity.id]), format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["host"]["id"], self.host.id)
        self.assertEqual(response.data["amenities"][0]["name"], "Wi-Fi")
        self.assertEqual(Property.objects.get(pk=response.data["id"]).host, self.host)

    def test_guest_and_anonymous_cannot_create(self):
        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.post(list_url(), property_payload(), format="json").status_code, 403)

        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(list_url(), property_payload(), format="json").status_code, 401)

    def test_invalid_payloads_rejected(self):
        self.client.force_authenticate(self.host)

        zero_price = self.client.post(list_url(), property_payload(price_per_night="0"), format="json")
        self.assertEqual(zero_price.status_code, 400)

        only_latitude = self.client.post(list_url(), property_payload(latitude="15.5"), format="json")
        self.assertEqual(only_latitude.status_code, 400)

    def test_public_list_shows_only_active_properties(self):
        active = make_property(self.host, title="Active place")
        make_property(self.host, title="Hidden place", is_active=False)

        response = self.client.get(list_url())  # bina login

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], active.id)

    def test_inactive_property_visible_only_to_owner(self):
        prop = make_property(self.host, is_active=False)

        self.assertEqual(self.client.get(detail_url(prop.pk)).status_code, 404)

        self.client.force_authenticate(self.host)
        self.assertEqual(self.client.get(detail_url(prop.pk)).status_code, 200)

    def test_update_permissions(self):
        prop = make_property(self.host)
        payload = {"price_per_night": "3000.00"}

        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.patch(detail_url(prop.pk), payload, format="json").status_code, 403)

        self.client.force_authenticate(self.other_host)
        self.assertEqual(self.client.patch(detail_url(prop.pk), payload, format="json").status_code, 403)

        self.client.force_authenticate(self.host)
        self.assertEqual(self.client.patch(detail_url(prop.pk), payload, format="json").status_code, 200)
        prop.refresh_from_db()
        self.assertEqual(prop.price_per_night, Decimal("3000.00"))

        self.client.force_authenticate(self.admin)
        self.assertEqual(
            self.client.patch(detail_url(prop.pk), {"price_per_night": "3500.00"}, format="json").status_code,
            200,
        )

    def test_my_listings_only_returns_own_including_inactive(self):
        make_property(self.host)
        make_property(self.host, is_active=False)
        make_property(self.other_host)

        self.client.force_authenticate(self.host)
        response = self.client.get(my_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)

        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.get(my_url()).status_code, 403)

        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(my_url()).status_code, 401)


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
class PropertyImageTests(PropertyAPITestCase):
    def test_multiple_upload_first_image_becomes_primary(self):
        prop = make_property(self.host)
        self.client.force_authenticate(self.host)

        response = self.upload(prop, count=2)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(response.data[0]["is_primary"])
        self.assertFalse(response.data[1]["is_primary"])
        self.assertEqual(prop.images.filter(is_primary=True).count(), 1)

    def test_non_image_file_rejected(self):
        prop = make_property(self.host)
        self.client.force_authenticate(self.host)
        fake = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")

        response = self.client.post(images_url(prop.pk), {"images": [fake]}, format="multipart")

        self.assertEqual(response.status_code, 400)

    def test_other_host_cannot_upload(self):
        prop = make_property(self.host)
        self.client.force_authenticate(self.other_host)

        self.assertEqual(self.upload(prop, count=1).status_code, 403)

    def test_set_primary_and_deleting_primary_promotes_next(self):
        prop = make_property(self.host)
        self.client.force_authenticate(self.host)
        ids = [item["id"] for item in self.upload(prop, count=2).data]

        # Doosri image primary karo
        response = self.client.patch(
            image_detail_url(prop.pk, ids[1]), {"is_primary": True}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(prop.images.filter(is_primary=True).values_list("id", flat=True)), [ids[1]])

        # Primary image delete karo: pehli image primary ban jaani chahiye
        response = self.client.delete(image_detail_url(prop.pk, ids[1]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(prop.images.filter(is_primary=True).values_list("id", flat=True)), [ids[0]])


# ---------------------------------------------------------------------------
# Delete rules
# ---------------------------------------------------------------------------
class PropertyDeleteTests(PropertyAPITestCase):
    def make_booking(self, prop, start_offset, end_offset, status):
        today = timezone.localdate()
        nights = end_offset - start_offset
        return Booking.objects.create(
            guest=self.guest,
            property=prop,
            check_in=today + timedelta(days=start_offset),
            check_out=today + timedelta(days=end_offset),
            num_guests=2,
            price_per_night=prop.price_per_night,
            total_price=prop.price_per_night * nights,
            status=status,
        )

    def test_property_without_bookings_is_deleted_permanently(self):
        prop = make_property(self.host)
        self.client.force_authenticate(self.host)

        response = self.client.delete(detail_url(prop.pk))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Property.objects.filter(pk=prop.pk).exists())

    def test_property_with_past_bookings_is_soft_deleted(self):
        prop = make_property(self.host)
        self.make_booking(prop, -10, -7, Booking.Status.COMPLETED)
        self.client.force_authenticate(self.host)

        response = self.client.delete(detail_url(prop.pk))

        self.assertEqual(response.status_code, 200)
        prop.refresh_from_db()
        self.assertFalse(prop.is_active)

    def test_property_with_upcoming_booking_cannot_be_deleted(self):
        prop = make_property(self.host)
        self.make_booking(prop, 5, 7, Booking.Status.CONFIRMED)
        self.client.force_authenticate(self.host)

        response = self.client.delete(detail_url(prop.pk))

        self.assertEqual(response.status_code, 400)
        prop.refresh_from_db()
        self.assertTrue(prop.is_active)


# ---------------------------------------------------------------------------
# Query performance (N+1 check)
# ---------------------------------------------------------------------------
class PropertyQueryTests(PropertyAPITestCase):
    def add_properties(self, count):
        for index in range(count):
            prop = make_property(self.host, title=f"Property number {index}")
            PropertyImage.objects.create(property=prop, image=make_image(f"p{index}.png"), is_primary=True)

    def count_list_queries(self):
        with CaptureQueriesContext(connection) as context:
            response = self.client.get(list_url())
        self.assertEqual(response.status_code, 200)
        return len(context)

    def test_list_query_count_does_not_grow_with_properties(self):
        self.add_properties(2)
        queries_for_two = self.count_list_queries()

        self.add_properties(4)  # ab total 6
        queries_for_six = self.count_list_queries()

        self.assertEqual(queries_for_two, queries_for_six)


# ---------------------------------------------------------------------------
# Amenities
# ---------------------------------------------------------------------------
class AmenityTests(PropertyAPITestCase):
    def test_public_can_list_amenities(self):
        Amenity.objects.create(name="Wi-Fi")
        response = self.client.get(reverse("properties:amenity-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_only_admin_can_create_amenity(self):
        url = reverse("properties:amenity-list")

        self.client.force_authenticate(self.guest)
        self.assertEqual(self.client.post(url, {"name": "Sauna"}, format="json").status_code, 403)

        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(url, {"name": "Sauna"}, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, {"name": "Sauna"}, format="json").status_code, 400)  # duplicate