import threading
from datetime import timedelta

from django.db import connection
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User

from . import services
from .models import ACTIVE_BOOKING_STATUSES, Booking
from .services import BookingConflict
from .tests import make_property, make_user


class BookingConcurrencyTests(TransactionTestCase):
    """
    TransactionTestCase kyunki threads ko real commits chahiye
    (normal TestCase ka wrapper transaction threads ko dikhta nahi).
    """

    def setUp(self):
        self.host = make_user("chost", User.Role.HOST)
        self.prop = make_property(self.host)
        self.guests = [make_user(f"cguest{i}") for i in range(5)]
        today = timezone.localdate()
        self.ci = today + timedelta(days=20)
        self.co = today + timedelta(days=23)

    def run_in_threads(self, tasks):
        barrier = threading.Barrier(len(tasks))
        results = [None] * len(tasks)

        def worker(index, task):
            try:
                barrier.wait(timeout=10)  # sab threads ek saath start
                task()
                results[index] = "ok"
            except BookingConflict:
                results[index] = "conflict"
            except Exception as exc:  # noqa: BLE001
                results[index] = f"error: {exc!r}"
            finally:
                connection.close()  # har thread ka apna DB connection

        threads = [
            threading.Thread(target=worker, args=(i, task)) for i, task in enumerate(tasks)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        return results

    def test_same_dates_only_one_succeeds(self):
        tasks = [
            (lambda g=g: services.create_booking(
                guest=g,
                property_id=self.prop.id,
                check_in=self.ci,
                check_out=self.co,
                num_guests=2,
            ))
            for g in self.guests
        ]
        results = self.run_in_threads(tasks)

        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(results.count("conflict"), 4, results)
        self.assertEqual(
            Booking.objects.filter(
                property=self.prop, status__in=ACTIVE_BOOKING_STATUSES
            ).count(),
            1,
        )

    def test_partially_overlapping_dates_only_one_succeeds(self):
        ranges = [(0, 3), (1, 4), (2, 5), (0, 2)]  # sab ek dusre se overlap karte hain
        tasks = [
            (lambda g=g, a=a, b=b: services.create_booking(
                guest=g,
                property_id=self.prop.id,
                check_in=self.ci + timedelta(days=a),
                check_out=self.ci + timedelta(days=b),
                num_guests=2,
            ))
            for g, (a, b) in zip(self.guests, ranges)
        ]
        results = self.run_in_threads(tasks)
        self.assertEqual(results.count("ok"), 1, results)
        self.assertEqual(results.count("conflict"), 3, results)

    def test_non_overlapping_dates_all_succeed(self):
        tasks = [
            (lambda g=g, i=i: services.create_booking(
                guest=g,
                property_id=self.prop.id,
                check_in=self.ci + timedelta(days=i * 3),
                check_out=self.ci + timedelta(days=i * 3 + 3),  # back-to-back
                num_guests=2,
            ))
            for i, g in enumerate(self.guests)
        ]
        results = self.run_in_threads(tasks)
        self.assertEqual(results.count("ok"), 5, results)