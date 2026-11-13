from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings import services as booking_services
from apps.bookings.tests import make_booking, make_property, make_user

from . import gateways
from .models import Payment


class MockGatewayTests(SimpleTestCase):
    def setUp(self):
        self.gateway = gateways.get_gateway("mock")

    def test_valid_signature_passes(self):
        sig = self.gateway.sign("order_1", "pay_1")
        self.assertTrue(
            self.gateway.verify_signature(order_id="order_1", payment_id="pay_1", signature=sig)
        )

    def test_tampered_signature_fails(self):
        sig = self.gateway.sign("order_1", "pay_1")
        self.assertFalse(
            self.gateway.verify_signature(order_id="order_1", payment_id="pay_1", signature=sig + "x")
        )

    def test_signature_bound_to_order_and_payment(self):
        sig = self.gateway.sign("order_1", "pay_1")
        self.assertFalse(
            self.gateway.verify_signature(order_id="order_2", payment_id="pay_1", signature=sig)
        )
        self.assertFalse(
            self.gateway.verify_signature(order_id="order_1", payment_id="pay_2", signature=sig)
        )

    def test_empty_signature_fails(self):
        self.assertFalse(
            self.gateway.verify_signature(order_id="order_1", payment_id="pay_1", signature="")
        )

    def test_unknown_provider(self):
        with self.assertRaises(ValueError):
            gateways.get_gateway("paypal")


@override_settings(PAYMENT_MOCK_ENABLED=True)
class PaymentBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.host = make_user("phost1", User.Role.HOST)
        cls.other_host = make_user("phost2", User.Role.HOST)
        cls.guest = make_user("pguest1")
        cls.other_guest = make_user("pguest2")
        cls.admin = make_user("padmin1", User.Role.ADMIN)
        cls.prop = make_property(cls.host)
        cls.other_prop = make_property(cls.other_host, title="Other villa")
        cls.today = timezone.localdate()
        cls.ci = cls.today + timedelta(days=10)
        cls.co = cls.today + timedelta(days=13)  # 3 nights x 2000 = 6000

    def setUp(self):
        self.client = APIClient()

    def login(self, user):
        self.client.force_authenticate(user=user)

    # ---- data helpers ----
    def confirmed_booking(self, guest=None, prop=None, ci=None, co=None, status="confirmed"):
        return make_booking(
            guest or self.guest,
            prop or self.prop,
            ci or self.ci,
            co or self.co,
            status=status,
        )

    # ---- API helpers ----
    def api_create(self, user, booking):
        self.login(user)
        return self.client.post(
            reverse("payments:payment-create"), {"booking": booking.id}, format="json"
        )

    def api_mock(self, user, tx, outcome="success"):
        self.login(user)
        return self.client.post(
            reverse("payments:payment-mock-checkout"),
            {"transaction_id": tx, "outcome": outcome},
            format="json",
        )

    def api_verify(self, user, tx, provider_payment_id, signature):
        self.login(user)
        return self.client.post(
            reverse("payments:payment-verify"),
            {
                "transaction_id": tx,
                "provider_payment_id": provider_payment_id,
                "signature": signature,
            },
            format="json",
        )

    def full_payment(self, user, booking):
        """create -> mock checkout -> verify. Returns transaction_id."""
        tx = self.api_create(user, booking).json()["payment"]["transaction_id"]
        mock = self.api_mock(user, tx).json()
        res = self.api_verify(user, tx, mock["provider_payment_id"], mock["signature"])
        assert res.status_code == 200, res.content
        return tx

    @staticmethod
    def cancel_via_api(client, booking, reason="Plans changed"):
        return client.post(
            reverse("bookings:booking-cancel", kwargs={"pk": booking.id}),
            {"reason": reason},
            format="json",
        )


# ---------------------------------------------------------------------------
# Create order
# ---------------------------------------------------------------------------
class CreatePaymentTests(PaymentBaseTestCase):
    def test_guest_creates_payment_for_confirmed_booking(self):
        booking = self.confirmed_booking()
        res = self.api_create(self.guest, booking)
        self.assertEqual(res.status_code, 201)
        body = res.json()
        self.assertEqual(body["payment"]["status"], "pending")
        self.assertEqual(body["payment"]["provider"], "mock")
        self.assertEqual(Decimal(body["payment"]["amount"]), Decimal("6000.00"))
        self.assertTrue(body["payment"]["provider_order_id"].startswith("mock_order_"))
        self.assertEqual(body["checkout"]["order_id"], body["payment"]["provider_order_id"])

    def test_amount_comes_from_booking_not_client(self):
        booking = self.confirmed_booking()
        self.login(self.guest)
        res = self.client.post(
            reverse("payments:payment-create"),
            {"booking": booking.id, "amount": "1.00"},
            format="json",
        )
        self.assertEqual(Decimal(res.json()["payment"]["amount"]), booking.total_price)

    def test_pending_payment_is_reused(self):
        booking = self.confirmed_booking()
        first = self.api_create(self.guest, booking)
        second = self.api_create(self.guest, booking)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(
            first.json()["payment"]["transaction_id"],
            second.json()["payment"]["transaction_id"],
        )
        self.assertEqual(Payment.objects.filter(booking=booking).count(), 1)

    def test_pending_booking_cannot_be_paid(self):
        booking = self.confirmed_booking(status="pending")
        self.assertEqual(self.api_create(self.guest, booking).status_code, 400)

    def test_cancelled_booking_cannot_be_paid(self):
        booking = self.confirmed_booking(status="cancelled")
        self.assertEqual(self.api_create(self.guest, booking).status_code, 400)

    def test_past_checkin_cannot_be_paid(self):
        past = self.today - timedelta(days=2)
        booking = self.confirmed_booking(ci=past, co=past + timedelta(days=3))
        self.assertEqual(self.api_create(self.guest, booking).status_code, 400)

    def test_other_guest_gets_404(self):
        booking = self.confirmed_booking()
        self.assertEqual(self.api_create(self.other_guest, booking).status_code, 404)

    def test_host_and_admin_forbidden(self):
        booking = self.confirmed_booking()
        self.assertEqual(self.api_create(self.host, booking).status_code, 403)
        self.assertEqual(self.api_create(self.admin, booking).status_code, 403)

    def test_unauthenticated_401(self):
        res = self.client.post(reverse("payments:payment-create"), {"booking": 1}, format="json")
        self.assertEqual(res.status_code, 401)

    def test_already_paid_returns_409(self):
        booking = self.confirmed_booking()
        self.full_payment(self.guest, booking)
        self.assertEqual(self.api_create(self.guest, booking).status_code, 409)

    def test_retry_after_failed_payment_creates_new(self):
        booking = self.confirmed_booking()
        tx1 = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        self.assertEqual(self.api_mock(self.guest, tx1, "failure").status_code, 402)
        res = self.api_create(self.guest, booking)
        self.assertEqual(res.status_code, 201)
        self.assertNotEqual(res.json()["payment"]["transaction_id"], tx1)


# ---------------------------------------------------------------------------
# Mock checkout
# ---------------------------------------------------------------------------
class MockCheckoutTests(PaymentBaseTestCase):
    def test_success_returns_payment_id_and_signature(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        res = self.api_mock(self.guest, tx)
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["outcome"], "success")
        self.assertTrue(body["provider_payment_id"].startswith("mock_pay_"))
        self.assertTrue(body["signature"])

    def test_failure_marks_payment_failed(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        self.assertEqual(self.api_mock(self.guest, tx, "failure").status_code, 402)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "failed")
        self.assertTrue(payment.failure_reason)

    def test_disabled_outside_dev(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        with self.settings(PAYMENT_MOCK_ENABLED=False):
            self.assertEqual(self.api_mock(self.guest, tx).status_code, 404)

    def test_other_guest_gets_404(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        self.assertEqual(self.api_mock(self.other_guest, tx).status_code, 404)


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
class VerifyPaymentTests(PaymentBaseTestCase):
    def test_full_flow_success(self):
        booking = self.confirmed_booking()
        tx = self.full_payment(self.guest, booking)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "success")
        self.assertIsNotNone(payment.paid_at)
        self.assertTrue(payment.provider_payment_id.startswith("mock_pay_"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "confirmed")

    def test_invalid_signature_marks_failed(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        res = self.api_verify(self.guest, tx, "mock_pay_fake", "bad-signature")
        self.assertEqual(res.status_code, 400)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.provider_payment_id, "")
        self.assertEqual(payment.provider_signature, "")

    def test_failed_payment_cannot_be_verified_later(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        mock = self.api_mock(self.guest, tx).json()
        self.api_verify(self.guest, tx, mock["provider_payment_id"], "bad")  # fail ho gaya
        res = self.api_verify(self.guest, tx, mock["provider_payment_id"], mock["signature"])
        self.assertEqual(res.status_code, 400)

    def test_verify_is_idempotent(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        mock = self.api_mock(self.guest, tx).json()
        first = self.api_verify(self.guest, tx, mock["provider_payment_id"], mock["signature"])
        second = self.api_verify(self.guest, tx, mock["provider_payment_id"], mock["signature"])
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["message"], "Payment was already verified.")
        self.assertEqual(Payment.objects.filter(booking=booking, status="success").count(), 1)

    def test_different_payment_id_after_success_returns_409(self):
        booking = self.confirmed_booking()
        tx = self.full_payment(self.guest, booking)
        payment = Payment.objects.get(transaction_id=tx)
        other_id = "mock_pay_other"
        sig = gateways.get_gateway("mock").sign(payment.provider_order_id, other_id)
        res = self.api_verify(self.guest, tx, other_id, sig)
        self.assertEqual(res.status_code, 409)

    def test_replay_of_used_payment_id_rejected(self):
        booking_a = self.confirmed_booking()
        tx_a = self.full_payment(self.guest, booking_a)
        used_id = Payment.objects.get(transaction_id=tx_a).provider_payment_id

        booking_b = self.confirmed_booking(
            ci=self.today + timedelta(days=20), co=self.today + timedelta(days=22)
        )
        tx_b = self.api_create(self.guest, booking_b).json()["payment"]["transaction_id"]
        order_b = Payment.objects.get(transaction_id=tx_b).provider_order_id
        # signature B ke order ke liye bilkul valid hai, phir bhi replay hona chahiye reject
        sig = gateways.get_gateway("mock").sign(order_b, used_id)
        res = self.api_verify(self.guest, tx_b, used_id, sig)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payment.objects.get(transaction_id=tx_b).status, "pending")

    def test_other_guest_cannot_verify(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        mock = self.api_mock(self.guest, tx).json()
        res = self.api_verify(self.other_guest, tx, mock["provider_payment_id"], mock["signature"])
        self.assertEqual(res.status_code, 404)

    def test_missing_fields_400(self):
        self.login(self.guest)
        res = self.client.post(reverse("payments:payment-verify"), {}, format="json")
        self.assertEqual(res.status_code, 400)

    def test_cancelled_booking_payment_cannot_be_verified(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        mock = self.api_mock(self.guest, tx).json()
        self.login(self.guest)
        self.assertEqual(self.cancel_via_api(self.client, booking).status_code, 200)
        res = self.api_verify(self.guest, tx, mock["provider_payment_id"], mock["signature"])
        self.assertEqual(res.status_code, 400)
        self.assertEqual(Payment.objects.get(transaction_id=tx).status, "failed")

    def test_db_allows_only_one_success_payment_per_booking(self):
        booking = self.confirmed_booking()
        Payment.objects.create(
            booking=booking,
            amount=Decimal("6000.00"),
            provider="mock",
            status="success",
            provider_order_id="o1",
            provider_payment_id="p1",
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Payment.objects.create(
                booking=booking,
                amount=Decimal("6000.00"),
                provider="mock",
                status="success",
                provider_order_id="o2",
                provider_payment_id="p2",
            )


# ---------------------------------------------------------------------------
# List / detail visibility
# ---------------------------------------------------------------------------
class PaymentVisibilityTests(PaymentBaseTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = reverse("payments:payment-list")

    def setUp(self):
        super().setUp()
        self.booking1 = self.confirmed_booking()
        self.tx1 = self.full_payment(self.guest, self.booking1)
        self.booking2 = self.confirmed_booking(
            guest=self.other_guest, prop=self.other_prop
        )
        self.tx2 = self.full_payment(self.other_guest, self.booking2)

    def tx_set(self, response):
        return {item["transaction_id"] for item in response.json()["results"]}

    def test_guest_sees_only_own(self):
        self.login(self.guest)
        self.assertEqual(self.tx_set(self.client.get(self.list_url)), {self.tx1})

    def test_host_sees_only_own_property_payments(self):
        self.login(self.host)
        self.assertEqual(self.tx_set(self.client.get(self.list_url)), {self.tx1})
        self.login(self.other_host)
        self.assertEqual(self.tx_set(self.client.get(self.list_url)), {self.tx2})

    def test_admin_sees_all(self):
        self.login(self.admin)
        self.assertEqual(self.tx_set(self.client.get(self.list_url)), {self.tx1, self.tx2})

    def test_filters(self):
        self.login(self.admin)
        res = self.client.get(self.list_url, {"booking": self.booking2.id})
        self.assertEqual(self.tx_set(res), {self.tx2})
        res = self.client.get(self.list_url, {"status": "refunded"})
        self.assertEqual(self.tx_set(res), set())

    def test_detail_own_ok_other_404(self):
        self.login(self.guest)
        ok = self.client.get(reverse("payments:payment-detail", kwargs={"transaction_id": self.tx1}))
        self.assertEqual(ok.status_code, 200)
        other = self.client.get(
            reverse("payments:payment-detail", kwargs={"transaction_id": self.tx2})
        )
        self.assertEqual(other.status_code, 404)

    def test_sensitive_fields_not_exposed(self):
        self.login(self.guest)
        item = self.client.get(self.list_url).json()["results"][0]
        self.assertNotIn("provider_signature", item)
        self.assertNotIn("raw_response", item)

    def test_list_requires_auth(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(self.list_url).status_code, 401)


# ---------------------------------------------------------------------------
# Refund on cancellation
# ---------------------------------------------------------------------------
class CancellationRefundTests(PaymentBaseTestCase):
    def paid_booking(self):
        booking = self.confirmed_booking()
        tx = self.full_payment(self.guest, booking)
        return booking, tx

    def test_guest_cancel_far_ahead_full_refund(self):
        booking, tx = self.paid_booking()
        self.login(self.guest)
        res = self.cancel_via_api(self.client, booking)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["refund_percentage"], 100)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(Decimal(payment.raw_response["refund"]["amount"]), Decimal("6000.00"))
        self.assertTrue(payment.raw_response["refund"]["refund_id"].startswith("mock_rfnd_"))

    def test_partial_refund_between_24_and_48_hours(self):
        booking, tx = self.paid_booking()
        check_in_dt = booking_services.get_check_in_datetime(booking)
        booking_services.cancel_booking(
            booking_id=booking.id,
            actor=self.guest,
            now=check_in_dt - timedelta(hours=30),
        )
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(payment.raw_response["refund"]["percentage"], 50)
        self.assertEqual(Decimal(payment.raw_response["refund"]["amount"]), Decimal("3000.00"))

    def test_no_refund_under_24_hours(self):
        booking, tx = self.paid_booking()
        check_in_dt = booking_services.get_check_in_datetime(booking)
        booking_services.cancel_booking(
            booking_id=booking.id,
            actor=self.guest,
            now=check_in_dt - timedelta(hours=5),
        )
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "success")  # refund nahi hua
        self.assertEqual(payment.raw_response["refund"]["percentage"], 0)
        self.assertEqual(Decimal(payment.raw_response["refund"]["amount"]), Decimal("0.00"))

    def test_host_cancel_gives_full_refund(self):
        booking, tx = self.paid_booking()
        self.login(self.host)
        res = self.cancel_via_api(self.client, booking, reason="Water supply issue")
        self.assertEqual(res.status_code, 200)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "refunded")
        self.assertEqual(Decimal(payment.raw_response["refund"]["amount"]), Decimal("6000.00"))

    def test_pending_payment_failed_on_cancel(self):
        booking = self.confirmed_booking()
        tx = self.api_create(self.guest, booking).json()["payment"]["transaction_id"]
        self.login(self.guest)
        self.cancel_via_api(self.client, booking)
        payment = Payment.objects.get(transaction_id=tx)
        self.assertEqual(payment.status, "failed")
        self.assertEqual(payment.failure_reason, "Booking was cancelled.")

    def test_cancel_without_payment_still_works(self):
        booking = self.confirmed_booking()
        self.login(self.guest)
        self.assertEqual(self.cancel_via_api(self.client, booking).status_code, 200)

    def test_refund_shown_in_payment_api(self):
        booking, tx = self.paid_booking()
        self.login(self.guest)
        self.cancel_via_api(self.client, booking)
        res = self.client.get(reverse("payments:payment-detail", kwargs={"transaction_id": tx}))
        body = res.json()
        self.assertEqual(body["status"], "refunded")
        self.assertEqual(body["refund"]["percentage"], 100)