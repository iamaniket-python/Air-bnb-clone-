from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.bookings.models import Booking

from .models import Amenity, PropertyAmenity, PropertyImage
from .tests import PropertyAPITestCase, detail_url, list_url, make_image, make_property


class PropertySearchTests(PropertyAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.wifi = Amenity.objects.create(name="Wi-Fi")
        cls.pool = Amenity.objects.create(name="Swimming Pool")

        cls.goa_villa = make_property(
            cls.host, title="Goa Villa", city="Goa", state="Goa", property_type="villa",
            price_per_night=Decimal("5000.00"), max_guests=6, average_rating=Decimal("4.80"),
        )
        cls.goa_flat = make_property(
            cls.host, title="Goa Flat", city="Panaji", state="Goa", property_type="apartment",
            price_per_night=Decimal("2000.00"), max_guests=2, average_rating=Decimal("3.50"),
        )
        cls.manali_house = make_property(
            cls.other_host, title="Manali House", city="Manali", state="Himachal Pradesh",
            property_type="house", price_per_night=Decimal("3000.00"), max_guests=4,
            average_rating=Decimal("4.20"),
        )

        PropertyAmenity.objects.create(property=cls.goa_villa, amenity=cls.wifi)
        PropertyAmenity.objects.create(property=cls.goa_villa, amenity=cls.pool)
        PropertyAmenity.objects.create(property=cls.goa_flat, amenity=cls.wifi)
        PropertyAmenity.objects.create(property=cls.manali_house, amenity=cls.pool)

    # -- helpers ------------------------------------------------------------
    def get(self, **params):
        return self.client.get(list_url(), params)

    def titles(self, **params):
        response = self.get(**params)
        self.assertEqual(response.status_code, 200, response.data)
        return sorted(item["title"] for item in response.data["results"])

    def day(self, offset):
        return (timezone.localdate() + timedelta(days=offset)).isoformat()

    def book(self, prop, start_day, end_day, status):
        today = timezone.localdate()
        return Booking.objects.create(
            guest=self.guest,
            property=prop,
            check_in=today + timedelta(days=start_day),
            check_out=today + timedelta(days=end_day),
            num_guests=2,
            price_per_night=prop.price_per_night,
            total_price=prop.price_per_night * (end_day - start_day),
            status=status,
        )

    # -- filters ------------------------------------------------------------
    def test_destination_matches_city_state_case_insensitive(self):
        self.assertEqual(self.titles(destination="goa"), ["Goa Flat", "Goa Villa"])
        self.assertEqual(self.titles(destination="PANAJI"), ["Goa Flat"])
        self.assertEqual(self.titles(destination="Manali, Himachal"), ["Manali House"])

    def test_price_range(self):
        self.assertEqual(self.titles(min_price=2500), ["Goa Villa", "Manali House"])
        self.assertEqual(self.titles(max_price=3000), ["Goa Flat", "Manali House"])
        self.assertEqual(self.titles(min_price=2500, max_price=3500), ["Manali House"])
        self.assertEqual(self.get(min_price=5000, max_price=1000).status_code, 400)

    def test_guests(self):
        self.assertEqual(self.titles(guests=5), ["Goa Villa"])
        self.assertEqual(self.titles(guests=3), ["Goa Villa", "Manali House"])
        self.assertEqual(self.get(guests=0).status_code, 400)

    def test_property_type_supports_multiple_values(self):
        self.assertEqual(self.titles(property_type=["villa", "house"]), ["Goa Villa", "Manali House"])
        self.assertEqual(self.get(property_type="castle").status_code, 400)

    def test_amenities_require_all_selected(self):
        self.assertEqual(self.titles(amenities=[self.wifi.id]), ["Goa Flat", "Goa Villa"])
        self.assertEqual(self.titles(amenities=[self.wifi.id, self.pool.id]), ["Goa Villa"])
        self.assertEqual(self.get(amenities=[999999]).status_code, 400)

    def test_min_rating(self):
        self.assertEqual(self.titles(min_rating=4), ["Goa Villa", "Manali House"])
        self.assertEqual(self.titles(min_rating=4.5), ["Goa Villa"])
        self.assertEqual(self.get(min_rating=5.5).status_code, 400)

    def test_free_text_search(self):
        self.assertEqual(self.titles(search="manali"), ["Manali House"])
        self.assertEqual(self.titles(search="himachal"), ["Manali House"])

    # -- availability -------------------------------------------------------
    def test_availability_excludes_overlapping_active_bookings(self):
        self.book(self.goa_villa, 10, 14, "confirmed")
        self.book(self.manali_house, 10, 14, "pending")
        self.book(self.goa_flat, 10, 14, "cancelled")  # cancelled dates block nahi karti

        self.assertEqual(self.titles(check_in=self.day(12), check_out=self.day(15)), ["Goa Flat"])

    def test_back_to_back_and_non_overlapping_dates_stay_available(self):
        self.book(self.goa_villa, 10, 14, "confirmed")

        # Check-in usi din jis din purani booking ka check-out hai
        self.assertIn("Goa Villa", self.titles(check_in=self.day(14), check_out=self.day(16)))
        # Booking se pehle ki dates
        self.assertIn("Goa Villa", self.titles(check_in=self.day(5), check_out=self.day(10)))
        # Poori booking ko cover karne wali window block hogi
        self.assertNotIn("Goa Villa", self.titles(check_in=self.day(8), check_out=self.day(20)))

    def test_invalid_date_params_return_400(self):
        cases = [
            {"check_in": self.day(5)},
            {"check_out": self.day(5)},
            {"check_in": self.day(5), "check_out": self.day(5)},
            {"check_in": self.day(7), "check_out": self.day(5)},
            {"check_in": self.day(-3), "check_out": self.day(2)},
            {"check_in": "not-a-date", "check_out": self.day(2)},
        ]
        for params in cases:
            with self.subTest(params=params):
                self.assertEqual(self.get(**params).status_code, 400)

    # -- ordering, pagination, detail ---------------------------------------
    def test_ordering(self):
        by_price = [item["title"] for item in self.get(ordering="price_per_night").data["results"]]
        self.assertEqual(by_price, ["Goa Flat", "Manali House", "Goa Villa"])

        by_rating = [item["title"] for item in self.get(ordering="-average_rating").data["results"]]
        self.assertEqual(by_rating, ["Goa Villa", "Manali House", "Goa Flat"])

        # Invalid field ignore hoti hai (error nahi)
        self.assertEqual(self.get(ordering="password").status_code, 200)

    def test_pagination_with_page_size(self):
        for index in range(10):
            make_property(self.host, title=f"Extra {index}")

        first = self.get(page_size=5)
        self.assertEqual(first.data["count"], 13)
        self.assertEqual(len(first.data["results"]), 5)
        self.assertIsNotNone(first.data["next"])

        self.assertEqual(len(self.get(page_size=5, page=3).data["results"]), 3)
        self.assertEqual(len(self.get(page_size=500).data["results"]), 13)  # max 50 par capped

    def test_filters_do_not_affect_detail_endpoint(self):
        response = self.client.get(
            detail_url(self.goa_villa.pk), {"min_price": 99999, "destination": "nowhere"}
        )
        self.assertEqual(response.status_code, 200)

    # -- performance --------------------------------------------------------
    def test_list_shows_primary_image_even_with_many_images(self):
        prop = make_property(self.host, title="Photo Place")
        PropertyImage.objects.create(property=prop, image=make_image("a.png"), display_order=0)
        primary = PropertyImage.objects.create(
            property=prop, image=make_image("b.png"), display_order=1, is_primary=True
        )
        PropertyImage.objects.create(property=prop, image=make_image("c.png"), display_order=2)

        response = self.get(search="Photo")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["results"][0]["primary_image"].endswith(primary.image.url))

    def test_query_count_stays_constant_with_all_filters(self):
        params = {
            "destination": "goa",
            "min_price": 1000,
            "amenities": [self.wifi.id],
            "check_in": self.day(20),
            "check_out": self.day(22),
            "ordering": "-average_rating",
        }

        def add_goa_properties(count, start):
            for index in range(start, start + count):
                prop = make_property(self.host, title=f"Goa extra {index}", city="Goa", state="Goa")
                PropertyAmenity.objects.create(property=prop, amenity=self.wifi)
                PropertyImage.objects.create(
                    property=prop, image=make_image(f"g{index}.png"), is_primary=True
                )

        def count_queries():
            with CaptureQueriesContext(connection) as context:
                response = self.client.get(list_url(), params)
            self.assertEqual(response.status_code, 200, response.data)
            return len(context)

        add_goa_properties(2, 0)
        count_queries()  # warm-up
        queries_with_few = count_queries()

        add_goa_properties(5, 2)
        queries_with_many = count_queries()

        self.assertEqual(queries_with_few, queries_with_many)

    # -- destinations autocomplete -------------------------------------------
    def test_destinations_autocomplete(self):
        url = reverse("properties:property-destinations")

        response = self.client.get(url, {"q": "go"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row["city"] for row in response.data}, {"Goa", "Panaji"})

        self.assertEqual(self.client.get(url, {"q": "g"}).data, [])  # bahut chhota query