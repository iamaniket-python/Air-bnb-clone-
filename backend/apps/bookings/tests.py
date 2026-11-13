from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.properties.models import Property

from . import services
from .models import Booking

PASSWORD = "StrongPass@123"


def make_user(username, role=User.Role.GUEST):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=PASSWORD,
        role=role,
    )


def make_property(host, **overrides):
    data = dict(
        host=host,
        title="Sea View Apartment",
        description="Lovely place near the beach.",
        property_type="apartment",
        address="1 Beach Road",
        city="Goa",
        state="Goa",
        country="India",
        postal_code="403001",
        price_per_night=Decimal("2000.00"),
        max_guests=4,
        bedrooms=2,
        beds=2,
        bathrooms=1,
    )
    data.update(overrides)
    return Property.objects.create(**data)


def make_booking(guest, prop, check_in, check_out, status="pending", num_guests=2):
    nights = (check_out - check_in).days
    return Booking.objects.create(
        guest=guest,
        property=prop,
        check_in=check_in,
        check_out=check_out,
        num_guests=num_guests,
        price_per_night=prop.price_per_night,
        total_price=prop.price_per_night * nights,
        status=status,
    )


class BookingBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = make_user("host1", User.Role.HOST)
        cls.other_host = make_user("host2", User.Role.HOST)
        cls.guest = make_user("guest1")
        cls.other_guest = make_user("guest2")
        cls.admin = make_user("admin1", User.Role.ADMIN)
        cls.prop = make_property(cls.host)
        cls.today = timezone.localdate()
        cls.ci = cls.today + timedelta(days=10)
        cls.co = cls.today + timedelta(days=13)  # 3 nights

    def setUp(self):
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user=user)

    def payload(self, **overrides):
        data = {
            "property": self.prop.id,
            "check_in": str(self.ci),
            "check_out": str(self.co),
            "num_guests": 2,
        }
        data.update(overrides)
        return data

    def create_via_api(self, user=None, **overrides):
        self.login(user or self.guest)
        return self.client.post(reverse("bookings:booking-list"), self.payload(**overrides), format="json")

    @staticmethod
    def detail_url(pk):
        return reverse("bookings:booking-detail", kwargs={"pk": pk})

    @staticmethod
    def status_url(pk):
        return reverse("bookings:booking-status", kwargs={"pk": pk})

    @staticmethod
    def cancel_url(pk):
        return reverse("bookings:booking-cancel", kwargs={"pk": pk})


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------
class QuoteTests(BookingBaseTestCase):
    url = reverse("bookings:booking-quote")

    def params(self, **overrides):
        data = {
            "property": self.prop.id,
            "check_in": str(self.ci),
            "check_out": str(self.co),
            "guests": 2,
        }
        data.update(overrides)
        return data

    def test_quote_is_public_and_calculates_price(self):
        res = self.client.get(self.url, self.params())
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["available"])
        self.assertEqual(body["nights"], 3)
        self.assertEqual(Decimal(body["total_price"]), Decimal("6000.00"))
        self.assertEqual(body["reasons"], [])

    def test_quote_unavailable_when_overlapping(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        res = self.client.get(self.url, self.params(check_in=str(self.ci + timedelta(days=1))))
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["available"])

    def test_quote_back_to_back_is_available(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        res = self.client.get(
            self.url,
            self.params(check_in=str(self.co), check_out=str(self.co + timedelta(days=2))),
        )
        self.assertTrue(res.json()["available"])

    def test_quote_ignores_rejected_and_cancelled(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="rejected")
        make_booking(self.guest, self.prop, self.ci, self.co, status="cancelled")
        res = self.client.get(self.url, self.params())
        self.assertTrue(res.json()["available"])

    def test_quote_too_many_guests(self):
        res = self.client.get(self.url, self.params(guests=9))
        self.assertFalse(res.json()["available"])

    def test_quote_inactive_property(self):
        self.prop.is_active = False
        self.prop.save()
        res = self.client.get(self.url, self.params())
        self.assertFalse(res.json()["available"])
        self.prop.is_active = True
        self.prop.save()

    def test_quote_past_dates_not_available(self):
        res = self.client.get(
            self.url,
            self.params(
                check_in=str(self.today - timedelta(days=3)),
                check_out=str(self.today - timedelta(days=1)),
            ),
        )
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()["available"])

    def test_quote_invalid_range_returns_400(self):
        res = self.client.get(self.url, self.params(check_in=str(self.co), check_out=str(self.ci)))
        self.assertEqual(res.status_code, 400)

    def test_quote_missing_params_returns_400(self):
        res = self.client.get(self.url, {"property": self.prop.id})
        self.assertEqual(res.status_code, 400)

    def test_quote_own_property_not_available_for_host(self):
        self.login(self.host)
        res = self.client.get(self.url, self.params())
        self.assertFalse(res.json()["available"])


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
class CreateBookingTests(BookingBaseTestCase):
    def test_guest_can_create_pending_booking(self):
        res = self.create_via_api()
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["status"], "pending")
        self.assertEqual(body["nights"], 3)
        self.assertEqual(Decimal(body["total_price"]), Decimal("6000.00"))
        self.assertEqual(body["guest"]["username"], "guest1")
        self.assertIn("cancel", body["available_actions"])

    def test_price_is_snapshot(self):
        res = self.create_via_api()
        self.prop.price_per_night = Decimal("5000.00")
        self.prop.save()
        booking = Booking.objects.get(pk=res.json()["id"])
        self.assertEqual(booking.price_per_night, Decimal("2000.00"))
        self.assertEqual(booking.total_price, Decimal("6000.00"))
        self.prop.price_per_night = Decimal("2000.00")
        self.prop.save()

    def test_unauthenticated_gets_401(self):
        res = self.client.post(reverse("bookings:booking-list"), self.payload(), format="json")
        self.assertEqual(res.status_code, 401)

    def test_host_and_admin_cannot_create(self):
        self.assertEqual(self.create_via_api(self.host).status_code, 403)
        self.assertEqual(self.create_via_api(self.admin).status_code, 403)

    def test_too_many_guests(self):
        res = self.create_via_api(num_guests=5)
        self.assertEqual(res.status_code, 400)
        self.assertIn("num_guests", res.json()["errors"])

    def test_past_checkin(self):
        res = self.create_via_api(
            check_in=str(self.today - timedelta(days=1)),
            check_out=str(self.today + timedelta(days=1)),
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("check_in", res.json()["errors"])

    def test_checkout_before_checkin(self):
        res = self.create_via_api(check_in=str(self.co), check_out=str(self.ci))
        self.assertEqual(res.status_code, 400)

    def test_max_stay_nights(self):
        res = self.create_via_api(check_out=str(self.ci + timedelta(days=31)))
        self.assertEqual(res.status_code, 400)

    def test_inactive_property(self):
        inactive = make_property(self.host, is_active=False, title="Hidden")
        res = self.create_via_api(property=inactive.id)
        self.assertEqual(res.status_code, 400)
        self.assertIn("property", res.json()["errors"])

    def test_unknown_property(self):
        res = self.create_via_api(property=999999)
        self.assertEqual(res.status_code, 400)

    def test_overlapping_booking_returns_409(self):
        self.assertEqual(self.create_via_api().status_code, 201)
        res = self.create_via_api(self.other_guest, check_in=str(self.ci + timedelta(days=1)))
        self.assertEqual(res.status_code, 409)

    def test_back_to_back_allowed(self):
        self.assertEqual(self.create_via_api().status_code, 201)
        res = self.create_via_api(
            self.other_guest,
            check_in=str(self.co),
            check_out=str(self.co + timedelta(days=2)),
        )
        self.assertEqual(res.status_code, 201)

    def test_rejected_booking_frees_dates(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="rejected")
        self.assertEqual(self.create_via_api(self.other_guest).status_code, 201)

    def test_cancelled_booking_frees_dates(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="cancelled")
        self.assertEqual(self.create_via_api(self.other_guest).status_code, 201)

    def test_db_exclusion_constraint_is_final_guard(self):
        make_booking(self.guest, self.prop, self.ci, self.co, status="pending")
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_booking(self.other_guest, self.prop, self.ci, self.co, status="confirmed")


# ---------------------------------------------------------------------------
# List / detail visibility
# ---------------------------------------------------------------------------
class BookingVisibilityTests(BookingBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.other_prop = make_property(cls.other_host, title="Other host villa")
        cls.b1 = make_booking(cls.guest, cls.prop, cls.ci, cls.co, status="pending")
        cls.b2 = make_booking(cls.other_guest, cls.other_prop, cls.ci, cls.co, status="confirmed")
        past_in = cls.today - timedelta(days=10)
        cls.b3 = make_booking(
            cls.guest, cls.prop, past_in, past_in + timedelta(days=2), status="completed"
        )
        cls.list_url = reverse("bookings:booking-list")

    def ids(self, response):
        return {item["id"] for item in response.json()["results"]}

    def test_guest_sees_only_own(self):
        self.login(self.guest)
        res = self.client.get(self.list_url)
        self.assertEqual(self.ids(res), {self.b1.id, self.b3.id})

    def test_host_sees_only_own_property_bookings(self):
        self.login(self.host)
        self.assertEqual(self.ids(self.client.get(self.list_url)), {self.b1.id, self.b3.id})
        self.login(self.other_host)
        self.assertEqual(self.ids(self.client.get(self.list_url)), {self.b2.id})

    def test_admin_sees_all(self):
        self.login(self.admin)
        self.assertEqual(
            self.ids(self.client.get(self.list_url)), {self.b1.id, self.b2.id, self.b3.id}
        )

    def test_list_requires_auth(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 401)

    def test_filter_by_status(self):
        self.login(self.guest)
        res = self.client.get(self.list_url, {"status": "completed"})
        self.assertEqual(self.ids(res), {self.b3.id})

    def test_filter_upcoming(self):
        self.login(self.guest)
        self.assertEqual(self.ids(self.client.get(self.list_url, {"upcoming": "true"})), {self.b1.id})
        self.assertEqual(self.ids(self.client.get(self.list_url, {"upcoming": "false"})), {self.b3.id})

    def test_pagination_shape(self):
        self.login(self.admin)
        body = self.client.get(self.list_url, {"page_size": 2}).json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["results"]), 2)

    def test_retrieve_own_ok_and_others_404(self):
        self.login(self.guest)
        self.assertEqual(self.client.get(self.detail_url(self.b1.id)).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(self.b2.id)).status_code, 404)

    def test_other_host_cannot_see_booking(self):
        self.login(self.other_host)
        self.assertEqual(self.client.get(self.detail_url(self.b1.id)).status_code, 404)


# ---------------------------------------------------------------------------
# Status change
# ---------------------------------------------------------------------------
class ChangeStatusTests(BookingBaseTestCase):
    def patch_status(self, user, booking, new_status, **extra):
        self.login(user)
        return self.client.patch(
            self.status_url(booking.id), {"status": new_status, **extra}, format="json"
        )

    def test_host_confirms_pending(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        res = self.patch_status(self.host, booking, "confirmed")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "confirmed")

    def test_host_rejects_with_reason_and_dates_freed(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        res = self.patch_status(self.host, booking, "rejected", reason="Maintenance work")
        self.assertEqual(res.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "rejected")
        self.assertEqual(booking.cancellation_reason, "Maintenance work")
        self.assertEqual(self.create_via_api(self.other_guest).status_code, 201)

    def test_admin_can_confirm(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.patch_status(self.admin, booking, "confirmed").status_code, 200)

    def test_guest_forbidden(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.patch_status(self.guest, booking, "confirmed").status_code, 403)

    def test_other_host_gets_404(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.patch_status(self.other_host, booking, "confirmed").status_code, 404)

    def test_pending_to_completed_invalid(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.patch_status(self.host, booking, "completed").status_code, 400)

    def test_confirmed_to_rejected_invalid(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        self.assertEqual(self.patch_status(self.host, booking, "rejected").status_code, 400)

    def test_invalid_status_value(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.patch_status(self.host, booking, "cancelled").status_code, 400)

    def test_cannot_confirm_past_checkin(self):
        past_in = self.today - timedelta(days=5)
        booking = make_booking(self.guest, self.prop, past_in, past_in + timedelta(days=2))
        self.assertEqual(self.patch_status(self.host, booking, "confirmed").status_code, 400)

    def test_cannot_complete_before_stay_ends(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        self.assertEqual(self.patch_status(self.host, booking, "completed").status_code, 400)

    def test_complete_after_stay_ended(self):
        past_in = self.today - timedelta(days=5)
        booking = make_booking(
            self.guest, self.prop, past_in, past_in + timedelta(days=2), status="confirmed"
        )
        res = self.patch_status(self.host, booking, "completed")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "completed")

    def test_terminal_status_cannot_change(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="rejected")
        self.assertEqual(self.patch_status(self.host, booking, "confirmed").status_code, 400)

    def test_available_actions_for_roles(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.login(self.guest)
        self.assertEqual(self.client.get(self.detail_url(booking.id)).json()["available_actions"], ["cancel"])
        self.login(self.host)
        self.assertEqual(
            self.client.get(self.detail_url(booking.id)).json()["available_actions"],
            ["confirm", "reject"],
        )


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------
class CancelBookingTests(BookingBaseTestCase):
    def cancel(self, user, booking, **body):
        self.login(user)
        return self.client.post(self.cancel_url(booking.id), body, format="json")

    def test_guest_cancels_pending_full_refund(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        res = self.cancel(self.guest, booking, reason="Plans changed")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["refund_percentage"], 100)
        self.assertEqual(body["booking"]["status"], "cancelled")
        booking.refresh_from_db()
        self.assertIsNotNone(booking.cancelled_at)
        self.assertEqual(booking.cancellation_reason, "Plans changed")

    def test_guest_cancels_confirmed_far_ahead_full_refund(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        res = self.cancel(self.guest, booking)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["refund_percentage"], 100)

    def test_cancel_frees_dates(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        self.cancel(self.guest, booking)
        self.assertEqual(self.create_via_api(self.other_guest).status_code, 201)

    def test_cancel_twice_fails(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.cancel(self.guest, booking)
        self.assertEqual(self.cancel(self.guest, booking).status_code, 400)

    def test_cannot_cancel_after_stay_started(self):
        past_in = self.today - timedelta(days=1)
        booking = make_booking(
            self.guest, self.prop, past_in, past_in + timedelta(days=3), status="confirmed"
        )
        self.assertEqual(self.cancel(self.guest, booking).status_code, 400)

    def test_other_guest_gets_404(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.cancel(self.other_guest, booking).status_code, 404)

    def test_host_cancel_confirmed_needs_reason(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        self.assertEqual(self.cancel(self.host, booking).status_code, 400)
        res = self.cancel(self.host, booking, reason="Water supply issue")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["refund_percentage"], 100)

    def test_host_cannot_cancel_pending(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co)
        self.assertEqual(self.cancel(self.host, booking, reason="No").status_code, 400)

    def test_admin_can_cancel_with_reason(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        res = self.cancel(self.admin, booking, reason="Policy violation")
        self.assertEqual(res.status_code, 200)

    def test_refund_percentage_tiers(self):
        booking = make_booking(self.guest, self.prop, self.ci, self.co, status="confirmed")
        check_in_dt = services.get_check_in_datetime(booking)
        cases = [(72, 100), (48, 100), (47, 50), (24, 50), (23, 0), (1, 0)]
        for hours, expected in cases:
            now = check_in_dt - timedelta(hours=hours)
            with self.subTest(hours_before=hours):
                self.assertEqual(
                    services.get_refund_percentage(booking, services.ROLE_GUEST, now), expected
                )

    def test_refund_pending_and_host_always_full(self):
        pending = make_booking(self.guest, self.prop, self.ci, self.co, status="pending")
        late = services.get_check_in_datetime(pending) - timedelta(hours=1)
        self.assertEqual(services.get_refund_percentage(pending, services.ROLE_GUEST, late), 100)
        pending.status = "confirmed"
        self.assertEqual(services.get_refund_percentage(pending, services.ROLE_HOST, late), 100)