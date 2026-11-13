import threading
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bookings.tests import make_property, make_user
from apps.properties.models import Property
from apps.reviews.models import Review
from apps.reviews.tests import make_completed_booking


class ConcurrentReviewTests(TransactionTestCase):
    """Threads wale tests TransactionTestCase mein (lesson 2)."""

    def setUp(self):
        self.host = make_user("chost", User.Role.HOST)
        self.prop = make_property(self.host)

    def _run_parallel(self, jobs):
        """jobs: [(user_id, booking_id, rating)]. Returns status codes list."""
        barrier = threading.Barrier(len(jobs))
        results, errors = [], []

        def worker(user_id, booking_id, rating):
            try:
                user = User.objects.get(pk=user_id)
                client = APIClient()
                client.force_authenticate(user=user)
                barrier.wait(timeout=15)
                resp = client.post(
                    "/api/reviews/",
                    {"booking": booking_id, "rating": rating, "comment": "parallel"},
                    format="json",
                )
                results.append(resp.status_code)
            except Exception as exc:  # noqa: BLE001
                errors.append(repr(exc))
            finally:
                connections.close_all()

        threads = [threading.Thread(target=worker, args=job) for job in jobs]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        self.assertEqual(errors, [])
        return results

    def test_parallel_reviews_keep_rating_correct(self):
        ratings = [5, 4, 3, 2, 1]
        jobs = []
        for i, rating in enumerate(ratings):
            guest = make_user(f"cguest{i}")
            booking = make_completed_booking(guest, self.prop, days_ago_out=2 + i * 4)
            jobs.append((guest.id, booking.id, rating))

        results = self._run_parallel(jobs)
        self.assertEqual(results, [201] * 5)

        prop = Property.objects.get(pk=self.prop.pk)
        self.assertEqual(prop.review_count, 5)
        self.assertEqual(prop.average_rating, Decimal("3.00"))

    def test_parallel_duplicate_reviews_only_one_wins(self):
        guest = make_user("dupguest")
        booking = make_completed_booking(guest, self.prop)
        jobs = [(guest.id, booking.id, 5)] * 4

        results = self._run_parallel(jobs)
        self.assertEqual(sorted(results), [201, 409, 409, 409])
        self.assertEqual(Review.objects.count(), 1)

        prop = Property.objects.get(pk=self.prop.pk)
        self.assertEqual(prop.review_count, 1)
        self.assertEqual(prop.average_rating, Decimal("5.00"))