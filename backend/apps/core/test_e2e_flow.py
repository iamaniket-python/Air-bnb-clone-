"""
End-to-end API flow (frontend jis sequence se chalta hai, wahi):
quote -> book -> host confirm -> pay (mock) -> complete -> review -> rating update.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.bookings.tests import make_property, make_user
from apps.properties.models import Property


@override_settings(PAYMENT_MOCK_ENABLED=True)
class GuestHostFlowTests(TestCase):
    def setUp(self):
        self.host = make_user("e2e_host", "host")
        self.guest = make_user("e2e_guest", "guest")
        self.property = make_property(self.host)

        self.guest_api = APIClient()
        self.guest_api.force_authenticate(self.guest)
        self.host_api = APIClient()
        self.host_api.force_authenticate(self.host)

        today = timezone.localdate()
        self.check_in = today + timedelta(days=10)
        self.check_out = today + timedelta(days=13)

    def test_full_booking_lifecycle(self):
        # 1. Quote (public endpoint, jaisa BookingWidget karta hai)
        quote = self.guest_api.get(
            "/api/bookings/quote/",
            {
                "property": self.property.id,
                "check_in": self.check_in.isoformat(),
                "check_out": self.check_out.isoformat(),
                "guests": 1,
            },
        )
        self.assertEqual(quote.status_code, 200, quote.content)
        self.assertTrue(quote.data["available"], quote.data)
        self.assertEqual(quote.data["nights"], 3)

        # 2. Guest booking request bhejta hai (Checkout page)
        created = self.guest_api.post(
            "/api/bookings/",
            {
                "property": self.property.id,
                "check_in": self.check_in.isoformat(),
                "check_out": self.check_out.isoformat(),
                "num_guests": 1,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        booking_id = created.data["id"]
        self.assertEqual(created.data["status"], "pending")
        # Server ka total, quote ke total ke barabar
        self.assertEqual(Decimal(str(created.data["total_price"])), Decimal(str(quote.data["total_price"])))

        # 3. Payment pending booking par allowed nahi (UI "Pay now" tab nahi dikhata)
        early = self.guest_api.post("/api/payments/create/", {"booking": booking_id}, format="json")
        self.assertEqual(early.status_code, 400, early.content)

        # 4. Host confirm karta hai (Host Reservations page)
        confirmed = self.host_api.patch(f"/api/bookings/{booking_id}/status/", {"status": "confirmed"}, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.content)

        # 5. Mock payment: create -> mock-checkout -> verify (Payment page ka 3-step flow)
        pay = self.guest_api.post("/api/payments/create/", {"booking": booking_id}, format="json")
        self.assertIn(pay.status_code, (200, 201), pay.content)
        txn = pay.data["payment"]["transaction_id"]

        checkout = self.guest_api.post(
            "/api/payments/mock-checkout/", {"transaction_id": txn, "outcome": "success"}, format="json"
        )
        self.assertEqual(checkout.status_code, 200, checkout.content)

        verify = self.guest_api.post(
            "/api/payments/verify/",
            {
                "transaction_id": checkout.data["transaction_id"],
                "provider_payment_id": checkout.data["provider_payment_id"],
                "signature": checkout.data["signature"],
            },
            format="json",
        )
        self.assertEqual(verify.status_code, 200, verify.content)

        # MyBookings ka "Paid" badge isi list se aata hai
        paid = self.guest_api.get("/api/payments/", {"booking": booking_id, "status": "success"})
        self.assertEqual(paid.status_code, 200)
        self.assertEqual(paid.data["count"], 1)

        # Dobara pay karna 409 (already paid)
        again = self.guest_api.post("/api/payments/create/", {"booking": booking_id}, format="json")
        self.assertEqual(again.status_code, 409, again.content)

        # 6. Stay khatam hui: dates ko past mein shift karo (API se past booking ban hi nahi sakti)
        past_out = timezone.localdate() - timedelta(days=2)
        Booking.objects.filter(pk=booking_id).update(check_in=past_out - timedelta(days=3), check_out=past_out)

        done = self.host_api.patch(f"/api/bookings/{booking_id}/status/", {"status": "completed"}, format="json")
        self.assertEqual(done.status_code, 200, done.content)

        # 7. Guest review likhta hai (ReviewModal). Backend comment ko required maanta hai.
        review = self.guest_api.post(
            "/api/reviews/", {"booking": booking_id, "rating": 4, "comment": "Nice stay."}, format="json"
        )
        self.assertEqual(review.status_code, 201, review.content)

        # Duplicate review 409 (valid payload ke saath, taaki validation error na aaye)
        dup = self.guest_api.post(
            "/api/reviews/", {"booking": booking_id, "rating": 5, "comment": "Again."}, format="json"
        )
        self.assertEqual(dup.status_code, 409, dup.content)

        # 8. Rating signals se update honi chahiye (Home "Top rated" + details page)
        self.property.refresh_from_db()
        self.assertEqual(self.property.review_count, 1)
        self.assertEqual(self.property.average_rating, Decimal("4.00"))

        public = self.guest_api.get(f"/api/properties/{self.property.id}/reviews/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data["count"], 1)

        # 9. Host dashboard mein earnings dikhni chahiye
        dash = self.host_api.get("/api/host/dashboard/")
        self.assertEqual(dash.status_code, 200, dash.content)
        self.assertGreater(Decimal(str(dash.data["earnings"]["total"])), Decimal("0"))

    def test_double_booking_same_dates_is_rejected(self):
        payload = {
            "property": self.property.id,
            "check_in": self.check_in.isoformat(),
            "check_out": self.check_out.isoformat(),
            "num_guests": 1,
        }
        first = self.guest_api.post("/api/bookings/", payload, format="json")
        self.assertEqual(first.status_code, 201, first.content)

        other = make_user("e2e_guest2", "guest")
        other_api = APIClient()
        other_api.force_authenticate(other)
        second = other_api.post("/api/bookings/", payload, format="json")
        self.assertEqual(second.status_code, 409, second.content)

    def test_wrong_roles_are_blocked(self):
        # Host booking nahi kar sakta, guest host dashboard nahi dekh sakta (UI guards ka backend side)
        res = self.host_api.post(
            "/api/bookings/",
            {
                "property": self.property.id,
                "check_in": self.check_in.isoformat(),
                "check_out": self.check_out.isoformat(),
                "num_guests": 1,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertEqual(self.guest_api.get("/api/host/dashboard/").status_code, 403)
        self.assertEqual(self.guest_api.get("/api/admin/dashboard/").status_code, 403)

    def test_property_model_is_importable(self):
        # Import-level sanity: Property ka rating field Decimal hai
        self.assertIsInstance(Property.objects.get(pk=self.property.pk).average_rating, (Decimal, int, float))