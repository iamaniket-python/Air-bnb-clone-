from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.bookings.tests import make_booking, make_property, make_user
from apps.payments.models import Payment
from apps.reviews.models import Review

HOST_URL = "/api/host/dashboard/"
ADMIN_URL = "/api/admin/dashboard/"
USERS_URL = "/api/admin/users/"
PROPS_URL = "/api/admin/properties/"


def make_payment(booking, amount, status="success", refund_amount=None):
    raw = {}
    if refund_amount is not None:
        raw = {
            "refund": {
                "percentage": 50,
                "amount": str(refund_amount),
                "refund_id": "rf_test",
                "refunded_at": None,
            }
        }
    return Payment.objects.create(
        booking=booking,
        amount=Decimal(str(amount)),
        status=status,
        paid_at=timezone.now() if status in ("success", "refunded") else None,
        raw_response=raw,
    )


class DashboardBase(APITestCase):
    def setUp(self):
        self.admin = make_user("dadmin", User.Role.ADMIN)
        self.host = make_user("dhost", User.Role.HOST)
        self.host2 = make_user("dhost2", User.Role.HOST)
        self.guest = make_user("dguest")
        self.guest2 = make_user("dguest2")
        self.client = APIClient()
        self.today = timezone.localdate()

    def login(self, user):
        self.client.force_authenticate(user=user)

    def booking(self, guest, prop, start, nights, status):
        return make_booking(
            guest,
            prop,
            self.today + timedelta(days=start),
            self.today + timedelta(days=start + nights),
            status=status,
        )


# ============================================================== HOST
class HostDashboardTests(DashboardBase):
    def test_permissions(self):
        self.assertEqual(self.client.get(HOST_URL).status_code, 401)
        for user in (self.guest, self.admin):
            self.login(user)
            self.assertEqual(self.client.get(HOST_URL).status_code, 403)

    def test_empty_host_gets_zeros(self):
        self.login(self.host)
        body = self.client.get(HOST_URL).json()
        self.assertEqual(body["properties"], {"total": 0, "active": 0})
        self.assertEqual(body["bookings"]["total"], 0)
        self.assertEqual(
            body["bookings"]["by_status"],
            {"pending": 0, "confirmed": 0, "rejected": 0, "cancelled": 0, "completed": 0},
        )
        self.assertEqual(body["earnings"]["net"], "0.00")
        self.assertEqual(body["recent_bookings"], [])

    def test_counts_and_breakdown_only_for_own_properties(self):
        prop = make_property(self.host)
        inactive = make_property(self.host, title="Hidden", is_active=False)
        other = make_property(self.host2, title="Other host")

        self.booking(self.guest, prop, 10, 2, "pending")        # upcoming + pending
        self.booking(self.guest, prop, 20, 2, "confirmed")      # upcoming
        self.booking(self.guest, prop, -30, 2, "confirmed")     # past confirmed -> upcoming nahi
        self.booking(self.guest, prop, -10, 3, "completed")
        self.booking(self.guest, inactive, 30, 2, "cancelled")
        self.booking(self.guest, other, 10, 2, "pending")       # doosre host ki

        self.login(self.host)
        body = self.client.get(HOST_URL).json()

        self.assertEqual(body["properties"], {"total": 2, "active": 1})
        self.assertEqual(body["bookings"]["total"], 5)
        self.assertEqual(body["bookings"]["upcoming_reservations"], 2)
        self.assertEqual(body["bookings"]["pending_requests"], 1)
        self.assertEqual(
            body["bookings"]["by_status"],
            {"pending": 1, "confirmed": 2, "rejected": 0, "cancelled": 1, "completed": 1},
        )

    def test_recent_bookings_limited_and_newest_first(self):
        prop = make_property(self.host)
        created = [self.booking(self.guest, prop, 10 + i * 5, 2, "pending") for i in range(7)]
        self.login(self.host)
        recent = self.client.get(HOST_URL).json()["recent_bookings"]
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0]["id"], created[-1].id)
        for key in ("property_title", "guest_username", "check_in", "status", "total_price"):
            self.assertIn(key, recent[0])

    def test_earnings_gross_refunded_net(self):
        prop = make_property(self.host)
        other = make_property(self.host2, title="Other host")

        b1 = self.booking(self.guest, prop, -60, 3, "completed")
        b2 = self.booking(self.guest, prop, -50, 3, "completed")
        b3 = self.booking(self.guest, prop, -40, 3, "cancelled")
        b4 = self.booking(self.guest, prop, -30, 3, "completed")
        b5 = self.booking(self.guest, prop, -20, 3, "confirmed")
        b6 = self.booking(self.guest, other, -60, 3, "completed")

        make_payment(b1, 4000, "success")
        make_payment(b2, 3000, "refunded", refund_amount="1500.00")   # 50% refund
        make_payment(b3, 5000, "refunded", refund_amount="5000.00")   # poora refund
        make_payment(b4, 2000, "success")                              # 0% refund = success hi
        make_payment(b5, 999, "failed")                                # count nahi
        make_payment(b6, 7777, "success")                              # doosre host ki

        self.login(self.host)
        earnings = self.client.get(HOST_URL).json()["earnings"]
        # gross = 4000 + 3000 + 5000 + 2000 = 14000, refunded = 1500 + 5000 = 6500
        self.assertEqual(earnings["gross"], "14000.00")
        self.assertEqual(earnings["refunded"], "6500.00")
        self.assertEqual(earnings["net"], "7500.00")
        self.assertEqual(earnings["currency"], "INR")

    def test_pending_payment_not_counted_and_bad_refund_data_safe(self):
        prop = make_property(self.host)
        b1 = self.booking(self.guest, prop, -30, 3, "completed")
        b2 = self.booking(self.guest, prop, -20, 3, "completed")
        make_payment(b1, 1000, "pending")
        refunded = make_payment(b2, 2000, "refunded", refund_amount="junk")
        self.login(self.host)
        earnings = self.client.get(HOST_URL).json()["earnings"]
        self.assertEqual(earnings["gross"], "2000.00")
        self.assertEqual(earnings["refunded"], "0.00")
        self.assertEqual(earnings["net"], "2000.00")
        self.assertEqual(refunded.status, "refunded")


# ============================================================= ADMIN
class AdminDashboardTests(DashboardBase):
    def test_permissions(self):
        self.assertEqual(self.client.get(ADMIN_URL).status_code, 401)
        for user in (self.guest, self.host):
            self.login(user)
            self.assertEqual(self.client.get(ADMIN_URL).status_code, 403)

    def test_platform_stats(self):
        prop = make_property(self.host)
        make_property(self.host, title="Hidden", is_active=False)

        b1 = self.booking(self.guest, prop, -30, 3, "completed")
        b2 = self.booking(self.guest2, prop, -20, 3, "completed")
        self.booking(self.guest, prop, 10, 2, "pending")

        Review.objects.create(booking=b1, rating=5, comment="great")
        Review.objects.create(booking=b2, rating=3, comment="ok")

        make_payment(b1, 2000, "success")
        make_payment(b2, 1000, "refunded", refund_amount="400.00")

        self.login(self.admin)
        body = self.client.get(ADMIN_URL).json()

        self.assertEqual(body["users"]["total"], 5)
        self.assertEqual(body["users"]["by_role"], {"guest": 2, "host": 2, "admin": 1})
        self.assertEqual(body["users"]["inactive"], 0)
        self.assertEqual(body["users"]["new_last_30_days"], 5)
        self.assertEqual(body["properties"], {"total": 2, "active": 1})
        self.assertEqual(body["bookings"]["total"], 3)
        self.assertEqual(body["bookings"]["by_status"]["completed"], 2)
        self.assertEqual(body["bookings"]["by_status"]["pending"], 1)
        self.assertEqual(body["reviews"], {"total": 2, "average_rating": "4.00"})
        self.assertEqual(
            body["payments"]["by_status"],
            {"pending": 0, "success": 1, "failed": 0, "refunded": 1},
        )
        self.assertEqual(body["payments"]["revenue"]["gross"], "3000.00")
        self.assertEqual(body["payments"]["revenue"]["refunded"], "400.00")
        self.assertEqual(body["payments"]["revenue"]["net"], "2600.00")

    def test_empty_platform_review_average(self):
        self.login(self.admin)
        body = self.client.get(ADMIN_URL).json()
        self.assertEqual(body["reviews"], {"total": 0, "average_rating": "0.00"})
        self.assertEqual(body["payments"]["revenue"]["net"], "0.00")


class AdminUserManagementTests(DashboardBase):
    def test_permissions(self):
        self.assertEqual(self.client.get(USERS_URL).status_code, 401)
        for user in (self.guest, self.host):
            self.login(user)
            self.assertEqual(self.client.get(USERS_URL).status_code, 403)
            self.assertEqual(
                self.client.patch(f"{USERS_URL}{self.guest2.id}/", {"is_active": False}, format="json").status_code,
                403,
            )

    def test_list_shape_filters_and_counts(self):
        prop = make_property(self.host)
        self.booking(self.guest, prop, 10, 2, "pending")
        self.booking(self.guest, prop, 20, 2, "pending")
        self.login(self.admin)

        body = self.client.get(USERS_URL).json()
        for key in ("count", "next", "previous", "results"):
            self.assertIn(key, body)
        self.assertEqual(body["count"], 5)
        self.assertNotIn("password", body["results"][0])

        hosts = self.client.get(USERS_URL + "?role=host").json()
        self.assertEqual(hosts["count"], 2)
        host_row = next(u for u in hosts["results"] if u["username"] == "dhost")
        self.assertEqual(host_row["property_count"], 1)

        guest_row = next(
            u for u in self.client.get(USERS_URL + "?role=guest").json()["results"]
            if u["username"] == "dguest"
        )
        self.assertEqual(guest_row["booking_count"], 2)

        self.assertEqual(self.client.get(USERS_URL + "?search=dguest2").json()["count"], 1)
        self.assertEqual(self.client.get(USERS_URL + "?is_active=false").json()["count"], 0)

    def test_get_user_detail_and_404(self):
        self.login(self.admin)
        resp = self.client.get(f"{USERS_URL}{self.guest.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["username"], "dguest")
        self.assertEqual(self.client.get(f"{USERS_URL}999999/").status_code, 404)

    def test_deactivate_and_reactivate(self):
        self.login(self.admin)
        url = f"{USERS_URL}{self.guest.id}/"
        resp = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["user"]["is_active"])
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.is_active)
        self.assertEqual(self.client.get(USERS_URL + "?is_active=false").json()["count"], 1)

        resp = self.client.patch(url, {"is_active": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.guest.refresh_from_db()
        self.assertTrue(self.guest.is_active)

    def test_role_change_guest_to_host(self):
        self.login(self.admin)
        resp = self.client.patch(f"{USERS_URL}{self.guest.id}/", {"role": "host"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.role, "host")

    def test_host_with_properties_cannot_become_guest(self):
        make_property(self.host)
        self.login(self.admin)
        resp = self.client.patch(f"{USERS_URL}{self.host.id}/", {"role": "guest"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("role", resp.json()["errors"])
        self.host.refresh_from_db()
        self.assertEqual(self.host.role, "host")

    def test_host_without_properties_can_become_guest(self):
        self.login(self.admin)
        resp = self.client.patch(f"{USERS_URL}{self.host2.id}/", {"role": "guest"}, format="json")
        self.assertEqual(resp.status_code, 200)

    def test_cannot_assign_admin_role(self):
        self.login(self.admin)
        resp = self.client.patch(f"{USERS_URL}{self.guest.id}/", {"role": "admin"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("role", resp.json()["errors"])
        self.guest.refresh_from_db()
        self.assertEqual(self.guest.role, "guest")

    def test_cannot_modify_self_or_other_admin(self):
        other_admin = make_user("dadmin2", User.Role.ADMIN)
        self.login(self.admin)
        for target in (self.admin, other_admin):
            resp = self.client.patch(f"{USERS_URL}{target.id}/", {"is_active": False}, format="json")
            self.assertEqual(resp.status_code, 400)
            target.refresh_from_db()
            self.assertTrue(target.is_active)

    def test_invalid_payloads(self):
        self.login(self.admin)
        url = f"{USERS_URL}{self.guest.id}/"
        for payload in ({}, {"role": "superman"}, {"is_active": "maybe"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.patch(url, payload, format="json").status_code, 400)
        self.assertEqual(
            self.client.patch(f"{USERS_URL}999999/", {"is_active": False}, format="json").status_code,
            404,
        )


class AdminPropertyManagementTests(DashboardBase):
    def setUp(self):
        super().setUp()
        self.p_active = make_property(self.host, title="Goa Villa")
        self.p_hidden = make_property(self.host2, title="Manali Cabin", is_active=False)

    def test_permissions(self):
        self.assertEqual(self.client.get(PROPS_URL).status_code, 401)
        for user in (self.guest, self.host):
            self.login(user)
            self.assertEqual(self.client.get(PROPS_URL).status_code, 403)
            self.assertEqual(
                self.client.patch(f"{PROPS_URL}{self.p_active.id}/", {"is_active": False}, format="json").status_code,
                403,
            )

    def test_list_includes_inactive_with_filters(self):
        self.login(self.admin)
        body = self.client.get(PROPS_URL).json()
        self.assertEqual(body["count"], 2)
        self.assertIn("host", body["results"][0])

        self.assertEqual(self.client.get(PROPS_URL + "?is_active=false").json()["count"], 1)
        self.assertEqual(self.client.get(PROPS_URL + "?is_active=true").json()["count"], 1)
        self.assertEqual(self.client.get(PROPS_URL + f"?host={self.host2.id}").json()["count"], 1)
        self.assertEqual(self.client.get(PROPS_URL + "?search=manali").json()["count"], 1)

    def test_toggle_listing(self):
        self.login(self.admin)
        resp = self.client.patch(f"{PROPS_URL}{self.p_active.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["property"]["is_active"])
        self.p_active.refresh_from_db()
        self.assertFalse(self.p_active.is_active)
        # public listing se hat jaati hai
        public_ids = [p["id"] for p in APIClient().get("/api/properties/").json()["results"]]
        self.assertNotIn(self.p_active.id, public_ids)

        resp = self.client.patch(f"{PROPS_URL}{self.p_hidden.id}/", {"is_active": True}, format="json")
        self.assertEqual(resp.status_code, 200)
        public_ids = [p["id"] for p in APIClient().get("/api/properties/").json()["results"]]
        self.assertIn(self.p_hidden.id, public_ids)

    def test_invalid_toggle(self):
        self.login(self.admin)
        url = f"{PROPS_URL}{self.p_active.id}/"
        self.assertEqual(self.client.patch(url, {}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"is_active": "x"}, format="json").status_code, 400)
        self.assertEqual(
            self.client.patch(f"{PROPS_URL}999999/", {"is_active": False}, format="json").status_code, 404
        )