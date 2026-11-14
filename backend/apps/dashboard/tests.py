from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.accounts.services import get_tokens_for_user
from apps.bookings.tests import make_booking, make_property, make_user
from apps.payments.models import Payment
from apps.reviews.models import Review

HOST_URL = "/api/host/dashboard/"
ADMIN_URL = "/api/admin/dashboard/"


def client_for(user=None):
    client = APIClient()
    if user:
        client.force_authenticate(user)
    return client


def future_booking(guest, prop, offset, status="confirmed", nights=2):
    today = timezone.localdate()
    return make_booking(
        guest, prop,
        today + timedelta(days=offset), today + timedelta(days=offset + nights),
        status=status,
    )


def past_booking(guest, prop, days_ago_out=10, status="completed", nights=2):
    today = timezone.localdate()
    out = today - timedelta(days=days_ago_out)
    return make_booking(guest, prop, out - timedelta(days=nights), out, status=status)


def make_payment(booking, amount, status="success", refund_amount=None, paid_at=None):
    raw = {}
    if refund_amount is not None:
        raw["refund"] = {
            "percentage": 50, "amount": str(refund_amount),
            "refund_id": "r1", "refunded_at": "2026-01-01T00:00:00Z",
        }
    return Payment.objects.create(
        booking=booking, amount=Decimal(str(amount)), status=status,
        paid_at=paid_at or timezone.now(), raw_response=raw,
    )


class DashboardBase(APITestCase):
    def setUp(self):
        self.host = make_user("dhost", User.Role.HOST)
        self.host2 = make_user("dhost2", User.Role.HOST)
        self.guest = make_user("dguest")
        self.admin = make_user("dadmin", User.Role.ADMIN)
        self.prop = make_property(self.host)
        self.other_prop = make_property(self.host2, title="Other host")


class HostDashboardPermissionTests(DashboardBase):
    def test_roles(self):
        self.assertEqual(client_for().get(HOST_URL).status_code, 401)
        self.assertEqual(client_for(self.guest).get(HOST_URL).status_code, 403)
        self.assertEqual(client_for(self.admin).get(HOST_URL).status_code, 403)
        self.assertEqual(client_for(self.host).get(HOST_URL).status_code, 200)


class HostDashboardCountTests(DashboardBase):
    def test_empty_host(self):
        body = client_for(self.host2).get(HOST_URL).json()
        # host2 ke paas ek property hai, par koi booking nahi
        self.assertEqual(body["properties"], {"total": 1, "active": 1, "inactive": 0})
        self.assertEqual(body["bookings"]["total"], 0)
        self.assertEqual(
            set(body["bookings"]["by_status"]),
            {"pending", "confirmed", "rejected", "cancelled", "completed"},
        )
        self.assertEqual(body["earnings"]["total"], "0.00")
        self.assertEqual(len(body["earnings"]["monthly"]), 6)
        self.assertEqual(body["reviews"], {"count": 0, "average_rating": "0.00"})
        self.assertEqual(body["next_reservations"], [])

    def test_property_counts(self):
        make_property(self.host, title="Hidden", is_active=False)
        body = client_for(self.host).get(HOST_URL).json()
        self.assertEqual(body["properties"], {"total": 2, "active": 1, "inactive": 1})

    def test_booking_counts_only_own_properties(self):
        future_booking(self.guest, self.prop, 10, "pending")
        future_booking(self.guest, self.prop, 20, "confirmed")
        past_booking(self.guest, self.prop, 10, "completed")
        past_booking(self.guest, self.prop, 40, "cancelled")
        future_booking(self.guest, self.other_prop, 10, "pending")  # doosre host ki
        body = client_for(self.host).get(HOST_URL).json()["bookings"]
        self.assertEqual(body["total"], 4)
        self.assertEqual(body["upcoming_reservations"], 2)
        self.assertEqual(body["pending_requests"], 1)
        self.assertEqual(
            body["by_status"],
            {"pending": 1, "confirmed": 1, "rejected": 0, "cancelled": 1, "completed": 1},
        )

    def test_past_pending_not_upcoming(self):
        past_booking(self.guest, self.prop, 10, "pending")
        body = client_for(self.host).get(HOST_URL).json()["bookings"]
        self.assertEqual(body["upcoming_reservations"], 0)
        self.assertEqual(body["pending_requests"], 0)

    def test_next_reservations_sorted_limited(self):
        for offset in (50, 10, 30, 20, 40, 60, 70):
            future_booking(self.guest, self.prop, offset)
        future_booking(self.guest, self.prop, 100, "cancelled")
        rows = client_for(self.host).get(HOST_URL).json()["next_reservations"]
        self.assertEqual(len(rows), 5)
        dates = [r["check_in"] for r in rows]
        self.assertEqual(dates, sorted(dates))
        self.assertEqual(rows[0]["guest"], "dguest")
        self.assertEqual(rows[0]["property"]["id"], self.prop.id)

    def test_reviews_summary(self):
        booking = past_booking(self.guest, self.prop)
        Review.objects.create(booking=booking, rating=4, comment="ok")
        body = client_for(self.host).get(HOST_URL).json()["reviews"]
        self.assertEqual(body, {"count": 1, "average_rating": "4.00"})

    def test_query_count_constant(self):
        future_booking(self.guest, self.prop, 10)

        def count():
            with CaptureQueriesContext(connection) as ctx:
                self.assertEqual(client_for(self.host).get(HOST_URL).status_code, 200)
            return len(ctx)

        baseline = count()
        for offset in (20, 30, 40, 50):
            future_booking(self.guest, self.prop, offset)
        self.assertEqual(count(), baseline)


class HostEarningsTests(DashboardBase):
    def earnings(self, user=None):
        return client_for(user or self.host).get(HOST_URL).json()["earnings"]

    def test_net_earnings(self):
        b = [past_booking(self.guest, self.prop, 10 + 10 * i) for i in range(5)]
        make_payment(b[0], 4000, "success")                          # 4000
        make_payment(b[1], 3000, "refunded", refund_amount="1500")   # 1500
        make_payment(b[2], 2000, "success", refund_amount="0.00")    # 2000 (0% refund)
        make_payment(b[3], 9999, "pending")                          # ignore
        make_payment(b[4], 8888, "failed")                           # ignore
        other = past_booking(self.guest, self.other_prop, 10)
        make_payment(other, 5000, "success")                         # doosre host ka
        self.assertEqual(self.earnings()["total"], "7500.00")
        self.assertEqual(self.earnings(self.host2)["total"], "5000.00")

    def test_full_refund_is_zero(self):
        b = past_booking(self.guest, self.prop)
        make_payment(b, 3000, "refunded", refund_amount="3000")
        self.assertEqual(self.earnings()["total"], "0.00")

    def test_refunded_without_amount_treated_full(self):
        b = past_booking(self.guest, self.prop)
        make_payment(b, 3000, "refunded")
        self.assertEqual(self.earnings()["total"], "0.00")

    def test_monthly_breakdown(self):
        b1 = past_booking(self.guest, self.prop, 10)
        b2 = past_booking(self.guest, self.prop, 20)
        b3 = past_booking(self.guest, self.prop, 30)
        two_months = timezone.now() - timedelta(days=62)
        make_payment(b1, 1000, "success")
        make_payment(b2, 500, "success", paid_at=two_months)
        make_payment(b3, 700, "success", paid_at=timezone.now() - timedelta(days=400))
        data = self.earnings()
        self.assertEqual(data["total"], "2200.00")        # purana payment total mein
        self.assertEqual(data["this_month"], "1000.00")
        months = {m["month"]: m["amount"] for m in data["monthly"]}
        self.assertEqual(len(months), 6)
        self.assertEqual(months[timezone.localtime(two_months).strftime("%Y-%m")], "500.00")
        total_in_window = sum(Decimal(v) for v in months.values())
        self.assertEqual(total_in_window, Decimal("1500.00"))  # 400 din purana bahar


class AdminDashboardTests(DashboardBase):
    def test_roles(self):
        self.assertEqual(client_for().get(ADMIN_URL).status_code, 401)
        self.assertEqual(client_for(self.guest).get(ADMIN_URL).status_code, 403)
        self.assertEqual(client_for(self.host).get(ADMIN_URL).status_code, 403)
        self.assertEqual(client_for(self.admin).get(ADMIN_URL).status_code, 200)

    def test_platform_stats(self):
        User.objects.filter(pk=self.guest.pk).update(is_active=False)
        make_property(self.host, title="Hidden", is_active=False)
        b1 = past_booking(self.guest, self.prop, 10)
        future_booking(self.guest, self.prop, 10, "pending")
        Review.objects.create(booking=b1, rating=5, comment="")
        make_payment(b1, 4000, "success")
        b2 = past_booking(self.guest, self.other_prop, 10)
        make_payment(b2, 3000, "refunded", refund_amount="1000")
        make_payment(past_booking(self.guest, self.other_prop, 30), 777, "failed")

        body = client_for(self.admin).get(ADMIN_URL).json()
        self.assertEqual(body["users"]["total"], 4)
        self.assertEqual(body["users"]["inactive"], 1)
        self.assertEqual(body["users"]["by_role"], {"guest": 1, "host": 2, "admin": 1})
        self.assertEqual(body["users"]["new_last_30_days"], 4)
        self.assertEqual(body["properties"], {"total": 3, "active": 2, "inactive": 1})
        self.assertEqual(body["bookings"]["total"], 4)
        self.assertEqual(body["bookings"]["upcoming"], 1)
        self.assertEqual(body["bookings"]["by_status"]["pending"], 1)
        self.assertEqual(body["reviews"], {"count": 1, "average_rating": "5.00"})
        self.assertEqual(body["payments"]["gross"], "7000.00")
        self.assertEqual(body["payments"]["refunded"], "1000.00")
        self.assertEqual(body["payments"]["net"], "6000.00")
        self.assertEqual(body["payments"]["by_status"]["failed"], 1)
        self.assertIn("generated_at", body)


class AdminUserManagementTests(DashboardBase):
    def test_permissions(self):
        self.assertEqual(client_for().get("/api/admin/users/").status_code, 401)
        self.assertEqual(client_for(self.host).get("/api/admin/users/").status_code, 403)
        self.assertEqual(client_for(self.guest).get("/api/admin/users/").status_code, 403)
        resp = client_for(self.guest).patch(
            f"/api/admin/users/{self.host.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_list_filters_search_and_counts(self):
        future_booking(self.guest, self.prop, 10)
        client = client_for(self.admin)
        self.assertEqual(client.get("/api/admin/users/").json()["count"], 4)
        self.assertEqual(client.get("/api/admin/users/?role=host").json()["count"], 2)
        self.assertEqual(client.get("/api/admin/users/?search=dguest").json()["count"], 1)
        self.assertEqual(client.get("/api/admin/users/?is_active=false").json()["count"], 0)
        rows = {r["username"]: r for r in client.get("/api/admin/users/").json()["results"]}
        self.assertEqual(rows["dhost"]["properties_count"], 1)
        self.assertEqual(rows["dguest"]["bookings_count"], 1)
        self.assertNotIn("password", rows["dguest"])

    def test_invalid_role_filter_400(self):
        resp = client_for(self.admin).get("/api/admin/users/?role=superman")
        self.assertEqual(resp.status_code, 400)

    def test_retrieve_and_404(self):
        client = client_for(self.admin)
        self.assertEqual(client.get(f"/api/admin/users/{self.guest.id}/").status_code, 200)
        self.assertEqual(client.get("/api/admin/users/999999/").status_code, 404)

    def test_deactivate_and_reactivate(self):
        client = client_for(self.admin)
        url = f"/api/admin/users/{self.guest.id}/"
        resp = client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertFalse(resp.json()["is_active"])
        self.guest.refresh_from_db()
        self.assertFalse(self.guest.is_active)
        resp = client.patch(url, {"is_active": True}, format="json")
        self.assertTrue(resp.json()["is_active"])

    def test_cannot_deactivate_self_or_admin(self):
        client = client_for(self.admin)
        resp = client.patch(f"/api/admin/users/{self.admin.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 400)
        other_admin = make_user("dadmin2", User.Role.ADMIN)
        resp = client.patch(f"/api/admin/users/{other_admin.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 400)
        other_admin.refresh_from_db()
        self.assertTrue(other_admin.is_active)

    def test_invalid_payload_400(self):
        client = client_for(self.admin)
        url = f"/api/admin/users/{self.guest.id}/"
        self.assertEqual(client.patch(url, {}, format="json").status_code, 400)
        self.assertEqual(client.patch(url, {"is_active": "abc"}, format="json").status_code, 400)

    def test_put_and_delete_not_allowed(self):
        client = client_for(self.admin)
        url = f"/api/admin/users/{self.guest.id}/"
        self.assertEqual(client.put(url, {"is_active": False}, format="json").status_code, 405)
        self.assertEqual(client.delete(url).status_code, 405)

    def test_deactivated_user_refresh_token_rejected(self):
        tokens = get_tokens_for_user(self.guest)
        client_for(self.admin).patch(
            f"/api/admin/users/{self.guest.id}/", {"is_active": False}, format="json"
        )
        resp = APIClient().post(
            "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(resp.status_code, 401)


class AdminPropertyManagementTests(DashboardBase):
    def test_permissions(self):
        self.assertEqual(client_for().get("/api/admin/properties/").status_code, 401)
        self.assertEqual(client_for(self.host).get("/api/admin/properties/").status_code, 403)

    def test_list_includes_inactive_and_filters(self):
        make_property(self.host, title="Hidden", city="Jaipur", is_active=False)
        future_booking(self.guest, self.prop, 10)
        client = client_for(self.admin)
        self.assertEqual(client.get("/api/admin/properties/").json()["count"], 3)
        self.assertEqual(client.get("/api/admin/properties/?is_active=false").json()["count"], 1)
        self.assertEqual(client.get("/api/admin/properties/?city=jaip").json()["count"], 1)
        self.assertEqual(client.get(f"/api/admin/properties/?host={self.host2.id}").json()["count"], 1)
        rows = {r["id"]: r for r in client.get("/api/admin/properties/").json()["results"]}
        self.assertEqual(rows[self.prop.id]["bookings_count"], 1)
        self.assertEqual(rows[self.prop.id]["host"]["username"], "dhost")

    def test_toggle_active_hides_from_public_list(self):
        client = client_for(self.admin)
        resp = client.patch(f"/api/admin/properties/{self.prop.id}/", {"is_active": False}, format="json")
        self.assertEqual(resp.status_code, 200, resp.json())
        self.assertFalse(resp.json()["is_active"])
        public = client_for().get("/api/properties/").json()
        self.assertNotIn(self.prop.id, [r["id"] for r in public["results"]])
        resp = client.patch(f"/api/admin/properties/{self.prop.id}/", {"is_active": True}, format="json")
        self.assertTrue(resp.json()["is_active"])
        public = client_for().get("/api/properties/").json()
        self.assertIn(self.prop.id, [r["id"] for r in public["results"]])

    def test_invalid_payload_and_404(self):
        client = client_for(self.admin)
        self.assertEqual(client.patch(f"/api/admin/properties/{self.prop.id}/", {}, format="json").status_code, 400)
        self.assertEqual(client.patch("/api/admin/properties/999999/", {"is_active": False}, format="json").status_code, 404)

    def test_host_cannot_patch(self):
        resp = client_for(self.host).patch(
            f"/api/admin/properties/{self.prop.id}/", {"is_active": False}, format="json"
        )
        self.assertEqual(resp.status_code, 403)