"""
N+1 guard: list endpoints par rows 2 se 6 karne par query count nahi badhna chahiye.
Exact number hardcode nahi karte (harmless query add hone par test na toote),
sirf ye check karte hain ki queries rows ke saath GROW nahi karti.
"""
from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.bookings.tests import make_property, make_user
from apps.properties.models import PropertyImage


class QueryCountGuardTests(TestCase):
    SMALL = 2
    LARGE = 6

    def setUp(self):
        self.today = timezone.localdate()
        self.host = make_user("qc_host", "host")
        self.guest = make_user("qc_guest", "guest")

        self.anon_api = APIClient()
        self.guest_api = APIClient()
        self.guest_api.force_authenticate(self.guest)
        self.host_api = APIClient()
        self.host_api.force_authenticate(self.host)

        self.property_count = 0
        self.booking_slot = 0
        self.booking_property = None

    # ---------- data builders ----------
    def _add_properties(self, n):
        created = []
        for _ in range(n):
            self.property_count += 1
            prop = make_property(self.host, title=f"QC property {self.property_count}")
            # sirf naam: asli upload nahi, par cover_image ka query path test hota hai
            PropertyImage.objects.create(property=prop, image=f"qc/{prop.id}.jpg", is_primary=True)
            created.append(prop)
        return created

    def _add_bookings(self, n):
        if self.booking_property is None:
            self.booking_property = self._add_properties(1)[0]
        for _ in range(n):
            start = self.today + timedelta(days=10 + self.booking_slot * 5)
            self.booking_slot += 1
            res = self.guest_api.post(
                "/api/bookings/",
                {
                    "property": self.booking_property.id,
                    "check_in": start.isoformat(),
                    "check_out": (start + timedelta(days=2)).isoformat(),
                    "num_guests": 1,
                },
                format="json",
            )
            self.assertEqual(res.status_code, 201, res.content)

    def _add_wishlist(self, n):
        for prop in self._add_properties(n):
            res = self.guest_api.post("/api/wishlist/", {"property": prop.id}, format="json")
            self.assertIn(res.status_code, (200, 201), res.content)

    # ---------- measurement ----------
    def _queries(self, api, url):
        with CaptureQueriesContext(connection) as ctx:
            res = api.get(url)
        self.assertEqual(res.status_code, 200, res.content)
        return [q["sql"] for q in ctx.captured_queries]

    def _assert_flat(self, api, url, grow):
        grow(self.SMALL)
        small = self._queries(api, url)
        grow(self.LARGE - self.SMALL)
        large = self._queries(api, url)

        sample = "\n".join(f"  {i + 1}. {sql[:160]}" for i, sql in enumerate(large[:30]))
        self.assertEqual(
            len(small),
            len(large),
            f"{url}: {len(small)} queries for {self.SMALL} rows but {len(large)} for {self.LARGE} rows (N+1?)\n"
            f"Queries for the larger run:\n{sample}",
        )

    # ---------- tests ----------
    def test_property_list_has_no_n_plus_one(self):
        self._assert_flat(self.anon_api, "/api/properties/", self._add_properties)

    def test_guest_booking_list_has_no_n_plus_one(self):
        self._assert_flat(self.guest_api, "/api/bookings/", self._add_bookings)

    def test_host_booking_list_has_no_n_plus_one(self):
        self._assert_flat(self.host_api, "/api/bookings/", self._add_bookings)

    def test_wishlist_has_no_n_plus_one(self):
        self._assert_flat(self.guest_api, "/api/wishlist/", self._add_wishlist)