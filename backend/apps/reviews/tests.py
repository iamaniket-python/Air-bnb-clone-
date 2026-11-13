from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.bookings.tests import make_booking, make_property, make_user
from apps.reviews.models import Review
from apps.reviews.services import REVIEW_WINDOW_DAYS

REVIEWS_URL = "/api/reviews/"


def property_reviews_url(property_id):
    return f"/api/properties/{property_id}/reviews/"


def make_completed_booking(guest, prop, days_ago_out=3):
    """Past ki completed booking (ORM se seedha). Stay 3 raat ki."""
    today = timezone.localdate()
    return make_booking(
        guest,
        prop,
        today - timedelta(days=days_ago_out + 3),
        today - timedelta(days=days_ago_out),
        status="completed",
    )


class ReviewTestBase(APITestCase):
    def setUp(self):
        self.host = make_user("host1", User.Role.HOST)
        self.guest = make_user("guest1")
        self.other_guest = make_user("guest2")
        self.admin = make_user("admin1", User.Role.ADMIN)
        self.prop = make_property(self.host)
        self.booking = make_completed_booking(self.guest, self.prop)
        self.client = APIClient()
        self._counter = 0

    def login(self, user):
        self.client.force_authenticate(user=user)

    def post_review(self, booking_id=None, rating=5, comment="Great stay!"):
        return self.client.post(
            REVIEWS_URL,
            {
                "booking": booking_id or self.booking.id,
                "rating": rating,
                "comment": comment,
            },
            format="json",
        )

    def add_orm_reviews(self, n, rating=4):
        """ORM se n reviews (alag guests, non-overlapping completed bookings)."""
        for _ in range(n):
            self._counter += 1
            guest = make_user(f"revguest{self._counter}")
            booking = make_completed_booking(
                guest, self.prop, days_ago_out=2 + self._counter * 4
            )
            Review.objects.create(booking=booking, rating=rating, comment="ok")


class ReviewCreateTests(ReviewTestBase):
    def test_guest_can_review_completed_booking(self):
        self.login(self.guest)
        resp = self.post_review()
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["rating"], 5)
        self.assertEqual(body["booking"], self.booking.id)
        self.assertEqual(body["property"]["id"], self.prop.id)
        self.assertEqual(body["reviewer"]["username"], "guest1")
        self.assertNotIn("email", body["reviewer"])
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("5.00"))
        self.assertEqual(self.prop.review_count, 1)

    def test_anonymous_gets_401(self):
        self.assertEqual(self.post_review().status_code, 401)

    def test_host_and_admin_cannot_review(self):
        for user in (self.host, self.admin):
            self.login(user)
            self.assertEqual(self.post_review().status_code, 403)
        self.assertEqual(Review.objects.count(), 0)

    def test_other_guests_booking_is_404(self):
        self.login(self.other_guest)
        self.assertEqual(self.post_review().status_code, 404)

    def test_nonexistent_booking_is_404(self):
        self.login(self.guest)
        self.assertEqual(self.post_review(booking_id=999999).status_code, 404)

    def test_only_completed_bookings_can_be_reviewed(self):
        self.login(self.guest)
        today = timezone.localdate()
        for i, status in enumerate(["pending", "confirmed", "cancelled", "rejected"]):
            check_in = today + timedelta(days=10 + i * 5)
            booking = make_booking(
                self.guest, self.prop, check_in, check_in + timedelta(days=2), status=status
            )
            with self.subTest(status=status):
                resp = self.post_review(booking_id=booking.id)
                self.assertEqual(resp.status_code, 400)
                self.assertIn("booking", resp.json()["errors"])
        self.assertEqual(Review.objects.count(), 0)

    def test_duplicate_review_is_409(self):
        self.login(self.guest)
        self.assertEqual(self.post_review().status_code, 201)
        resp = self.post_review(rating=1)
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(Review.objects.count(), 1)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.review_count, 1)
        self.assertEqual(self.prop.average_rating, Decimal("5.00"))

    def test_rating_bounds_invalid(self):
        self.login(self.guest)
        for bad in [0, 6, -1, "abc", None, ""]:
            with self.subTest(rating=bad):
                resp = self.post_review(rating=bad)
                self.assertEqual(resp.status_code, 400)
                self.assertIn("rating", resp.json()["errors"])
        self.assertEqual(Review.objects.count(), 0)

    def test_rating_boundaries_valid(self):
        self.login(self.guest)
        self.assertEqual(self.post_review(rating=1).status_code, 201)
        booking2 = make_completed_booking(self.guest, self.prop, days_ago_out=10)
        self.assertEqual(self.post_review(booking_id=booking2.id, rating=5).status_code, 201)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("3.00"))

    def test_comment_required(self):
        self.login(self.guest)
        for bad in ["", "   ", None]:
            with self.subTest(comment=bad):
                resp = self.post_review(comment=bad)
                self.assertEqual(resp.status_code, 400)
                self.assertIn("comment", resp.json()["errors"])

    def test_review_window(self):
        self.login(self.guest)
        late = make_completed_booking(
            self.guest, self.prop, days_ago_out=REVIEW_WINDOW_DAYS + 5
        )
        resp = self.post_review(booking_id=late.id)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("booking", resp.json()["errors"])

        edge = make_completed_booking(self.guest, self.prop, days_ago_out=REVIEW_WINDOW_DAYS)
        self.assertEqual(self.post_review(booking_id=edge.id).status_code, 201)


class RatingAggregateTests(ReviewTestBase):
    def _review_as(self, user, booking, rating):
        self.login(user)
        resp = self.post_review(booking_id=booking.id, rating=rating)
        self.assertEqual(resp.status_code, 201)

    def test_average_rounds_half_up(self):
        self._review_as(self.guest, self.booking, 5)
        b2 = make_completed_booking(self.other_guest, self.prop, days_ago_out=10)
        self._review_as(self.other_guest, b2, 4)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("4.50"))
        self.assertEqual(self.prop.review_count, 2)

    def test_average_with_three_reviews(self):
        third = make_user("guest3")
        b2 = make_completed_booking(self.other_guest, self.prop, days_ago_out=10)
        b3 = make_completed_booking(third, self.prop, days_ago_out=20)
        self._review_as(self.guest, self.booking, 5)
        self._review_as(self.other_guest, b2, 4)
        self._review_as(third, b3, 4)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("4.33"))
        self.assertEqual(self.prop.review_count, 3)

    def test_reviews_of_other_property_do_not_mix(self):
        other_prop = make_property(self.host, title="Another")
        b2 = make_completed_booking(self.other_guest, other_prop)
        self._review_as(self.guest, self.booking, 5)
        self._review_as(self.other_guest, b2, 1)
        self.prop.refresh_from_db()
        other_prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("5.00"))
        self.assertEqual(other_prop.average_rating, Decimal("1.00"))

    def test_properties_api_reflects_new_rating(self):
        self._review_as(self.guest, self.booking, 4)
        anon = APIClient()

        listing = anon.get("/api/properties/").json()
        item = next(p for p in listing["results"] if p["id"] == self.prop.id)
        self.assertEqual(float(item["average_rating"]), 4.0)
        self.assertEqual(item["review_count"], 1)

        detail = anon.get(f"/api/properties/{self.prop.id}/").json()
        self.assertEqual(float(detail["average_rating"]), 4.0)
        self.assertEqual(detail["review_count"], 1)


class PropertyReviewListTests(ReviewTestBase):
    def test_public_list_newest_first_with_summary(self):
        self.login(self.guest)
        self.post_review(rating=5, comment="first")
        b2 = make_completed_booking(self.other_guest, self.prop, days_ago_out=10)
        self.login(self.other_guest)
        self.post_review(booking_id=b2.id, rating=3, comment="second")

        anon = APIClient()
        resp = anon.get(property_reviews_url(self.prop.id))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for key in ("count", "next", "previous", "results", "summary"):
            self.assertIn(key, body)
        self.assertEqual(body["count"], 2)
        self.assertEqual([r["comment"] for r in body["results"]], ["second", "first"])
        self.assertEqual(float(body["summary"]["average_rating"]), 4.0)
        self.assertEqual(body["summary"]["review_count"], 2)
        reviewer = body["results"][0]["reviewer"]
        self.assertNotIn("email", reviewer)
        self.assertEqual(reviewer["username"], "guest2")

    def test_pagination_page_size(self):
        self.add_orm_reviews(3)
        resp = APIClient().get(property_reviews_url(self.prop.id) + "?page_size=2")
        body = resp.json()
        self.assertEqual(body["count"], 3)
        self.assertEqual(len(body["results"]), 2)
        self.assertIsNotNone(body["next"])

    def test_nonexistent_property_404(self):
        self.assertEqual(APIClient().get(property_reviews_url(999999)).status_code, 404)

    def test_inactive_property_visibility(self):
        self.prop.is_active = False
        self.prop.save()
        self.assertEqual(APIClient().get(property_reviews_url(self.prop.id)).status_code, 404)
        self.login(self.guest)
        self.assertEqual(self.client.get(property_reviews_url(self.prop.id)).status_code, 404)
        self.login(self.host)
        self.assertEqual(self.client.get(property_reviews_url(self.prop.id)).status_code, 200)
        self.login(self.admin)
        self.assertEqual(self.client.get(property_reviews_url(self.prop.id)).status_code, 200)

    def test_no_n_plus_one(self):
        self.add_orm_reviews(2)
        with CaptureQueriesContext(connection) as small:
            APIClient().get(property_reviews_url(self.prop.id))
        self.add_orm_reviews(4)
        with CaptureQueriesContext(connection) as big:
            APIClient().get(property_reviews_url(self.prop.id))
        self.assertEqual(len(small.captured_queries), len(big.captured_queries))


class MyReviewsTests(ReviewTestBase):
    def test_guest_sees_only_own_reviews(self):
        self.login(self.guest)
        self.post_review()
        b2 = make_completed_booking(self.other_guest, self.prop, days_ago_out=10)
        self.login(self.other_guest)
        self.post_review(booking_id=b2.id, rating=2)

        self.login(self.guest)
        resp = self.client.get(REVIEWS_URL + "my/")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["results"][0]["reviewer"]["username"], "guest1")

    def test_my_reviews_needs_guest(self):
        self.assertEqual(APIClient().get(REVIEWS_URL + "my/").status_code, 401)
        self.login(self.host)
        self.assertEqual(self.client.get(REVIEWS_URL + "my/").status_code, 403)


class ReviewModerationTests(ReviewTestBase):
    def _create_two(self):
        self.login(self.guest)
        self.post_review(rating=5)
        b2 = make_completed_booking(self.other_guest, self.prop, days_ago_out=10)
        self.login(self.other_guest)
        self.post_review(booking_id=b2.id, rating=3)
        return Review.objects.order_by("id")

    def test_admin_can_list_with_filters(self):
        self._create_two()
        self.login(self.admin)
        resp = self.client.get(REVIEWS_URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 2)
        resp = self.client.get(REVIEWS_URL + "?rating=3")
        self.assertEqual(resp.json()["count"], 1)
        resp = self.client.get(REVIEWS_URL + f"?property={self.prop.id}")
        self.assertEqual(resp.json()["count"], 2)

    def test_non_admin_cannot_list_or_delete(self):
        reviews = self._create_two()
        for user in (self.guest, self.host):
            self.login(user)
            self.assertEqual(self.client.get(REVIEWS_URL).status_code, 403)
            self.assertEqual(
                self.client.delete(f"{REVIEWS_URL}{reviews[0].id}/").status_code, 403
            )
        self.assertEqual(Review.objects.count(), 2)

    def test_admin_delete_recomputes_rating(self):
        reviews = self._create_two()
        self.login(self.admin)
        resp = self.client.delete(f"{REVIEWS_URL}{reviews[0].id}/")  # rating 5 wala
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["property"]["review_count"], 1)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("3.00"))
        self.assertEqual(self.prop.review_count, 1)

    def test_deleting_last_review_resets_to_zero(self):
        self.login(self.guest)
        self.post_review(rating=5)
        review = Review.objects.get()
        self.login(self.admin)
        self.assertEqual(self.client.delete(f"{REVIEWS_URL}{review.id}/").status_code, 200)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("0.00"))
        self.assertEqual(self.prop.review_count, 0)

    def test_delete_unknown_review_404(self):
        self.login(self.admin)
        self.assertEqual(self.client.delete(f"{REVIEWS_URL}999999/").status_code, 404)

    def test_orm_delete_triggers_signal(self):
        """Django admin se delete karne par bhi rating sahi rehni chahiye."""
        reviews = self._create_two()
        reviews[1].delete()  # rating 3 wala, ORM se
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.average_rating, Decimal("5.00"))
        self.assertEqual(self.prop.review_count, 1)