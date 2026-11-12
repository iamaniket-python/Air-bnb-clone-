"""
Phase 2 verification: signals, relationships aur DB constraints.
Run: python verify_phase2.py
Saara test data end mein rollback ho jata hai.
"""
import os
from datetime import date, timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.exceptions import ValidationError  # noqa: E402
from django.db import IntegrityError, transaction  # noqa: E402

from apps.accounts.models import User  # noqa: E402
from apps.bookings.models import Booking  # noqa: E402
from apps.payments.models import Payment  # noqa: E402
from apps.properties.models import Amenity, Property, PropertyAmenity  # noqa: E402
from apps.reviews.models import Review  # noqa: E402


def ok(message):
    print(f"  [PASS] {message}")


def must_fail(label, func):
    """func() par IntegrityError aani chahiye, nahi aayi to test fail."""
    try:
        with transaction.atomic():
            func()
    except IntegrityError:
        ok(label)
    else:
        raise AssertionError(f"FAILED: {label}")


print("Phase 2 verification shuru...\n")

with transaction.atomic():
    # 1. Users + signals
    host = User.objects.create_user(
        username="v_host", email="v_host@test.com", password="Test@12345", role=User.Role.HOST
    )
    guest = User.objects.create_user(
        username="v_guest", email="v_guest@test.com", password="Test@12345"
    )
    assert host.profile and guest.profile
    assert host.wishlist and guest.wishlist
    ok("Signals: UserProfile aur Wishlist auto-create hue")

    # 2. Property + amenities (M2M through)
    prop = Property.objects.create(
        host=host,
        title="Test Villa",
        description="Beach ke paas",
        property_type=Property.PropertyType.VILLA,
        address="1 Beach Road",
        city="Goa",
        state="Goa",
        price_per_night=Decimal("2500.00"),
        max_guests=4,
    )
    wifi = Amenity.objects.create(name="Wi-Fi", icon="FaWifi")
    PropertyAmenity.objects.create(property=prop, amenity=wifi)
    assert prop.amenities.count() == 1
    ok("Property + Amenity (Many-to-Many through table) kaam kar raha hai")

    # 3. Role validation
    try:
        Property(
            host=guest,
            title="Bad",
            description="x",
            address="x",
            city="x",
            state="x",
            price_per_night=Decimal("100"),
        ).full_clean()
        raise AssertionError("Guest property owner ban gaya!")
    except ValidationError:
        ok("Non-host user property own nahi kar sakta (clean validation)")

    # 4. Bookings
    start = date.today() + timedelta(days=10)

    def make_booking(check_in, check_out, status=Booking.Status.CONFIRMED):
        nights = (check_out - check_in).days
        return Booking.objects.create(
            guest=guest,
            property=prop,
            check_in=check_in,
            check_out=check_out,
            num_guests=2,
            price_per_night=prop.price_per_night,
            total_price=prop.price_per_night * nights,
            status=status,
        )

    b1 = make_booking(start, start + timedelta(days=3))
    ok("Pehli booking ban gayi")

    must_fail(
        "Overlapping booking DB ne block ki (double booking protection)",
        lambda: make_booking(start + timedelta(days=1), start + timedelta(days=4)),
    )

    b2 = make_booking(start + timedelta(days=3), start + timedelta(days=5))
    ok("Back-to-back booking allowed (check-out din = agla check-in din)")

    make_booking(
        start + timedelta(days=1),
        start + timedelta(days=2),
        status=Booking.Status.CANCELLED,
    )
    ok("Cancelled booking dates ko block nahi karti")

    try:
        Booking(
            guest=guest,
            property=prop,
            check_in=start,
            check_out=start,
            num_guests=2,
            price_per_night=prop.price_per_night,
            total_price=Decimal("0"),
        ).full_clean()
        raise AssertionError("Invalid dates accept ho gayi!")
    except ValidationError:
        ok("check_out <= check_in reject hua (validation)")

    # 5. Payments
    # must_fail(
    #     "Check: failed payment baad ke success se pehle allowed hai",
    #     lambda: (_ for _ in ()).throw(IntegrityError()),
    # ) if False else None

    Payment.objects.create(booking=b2, amount=b2.total_price, status=Payment.Status.FAILED)
    Payment.objects.create(
        booking=b2,
        amount=b2.total_price,
        status=Payment.Status.SUCCESS,
        provider_payment_id="pay_test_b2",
    )
    ok("Failed attempt ke baad retry success allowed")

    Payment.objects.create(
        booking=b1,
        amount=b1.total_price,
        status=Payment.Status.SUCCESS,
        provider_payment_id="pay_test_b1",
    )
    must_fail(
        "Ek booking par doosra successful payment block hua",
        lambda: Payment.objects.create(
            booking=b1,
            amount=b1.total_price,
            status=Payment.Status.SUCCESS,
            provider_payment_id="pay_test_other",
        ),
    )
    must_fail(
        "Same provider_payment_id dobara use nahi ho sakti (replay protection)",
        lambda: Payment.objects.create(
            booking=b2,
            amount=b2.total_price,
            status=Payment.Status.FAILED,
            provider_payment_id="pay_test_b1",
        ),
    )

    # 6. Reviews
    Review.objects.create(booking=b1, rating=5, comment="Great stay")
    must_fail(
        "Ek booking par duplicate review block hua",
        lambda: Review.objects.create(booking=b1, rating=4),
    )
    must_fail(
        "Rating 6 reject hui (1-5 constraint)",
        lambda: Review.objects.create(booking=b2, rating=6),
    )

    print("\nSab checks pass. Test data rollback ho raha hai...")
    transaction.set_rollback(True)

print("Done.")