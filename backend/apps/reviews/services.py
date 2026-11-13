from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.bookings.models import Booking
from apps.properties.models import Property

from .models import Review

# Check-out ke baad itne din tak review likha ja sakta hai
REVIEW_WINDOW_DAYS = 30
STATUS_COMPLETED = "completed"  # plain string (enum lesson)


class ReviewConflict(APIException):
    status_code = 409
    default_detail = "You have already reviewed this booking."
    default_code = "review_conflict"


def get_review_queryset():
    """Saari review queries ek jagah: N+1 se bachne ke liye select_related."""
    return Review.objects.select_related(
        "booking__guest", "booking__property"
    ).order_by("-created_at", "-id")


def lock_property(property_id):
    """Property row par lock. Isi se concurrent reviews serialize hote hain."""
    return list(
        Property.objects.select_for_update()
        .filter(pk=property_id)
        .values_list("pk", flat=True)
    )


def recalculate_property_rating(property_id):
    """
    Property.average_rating / review_count ko reviews se dobara calculate karta hai.
    Atomic + property lock ke saath. Returns (average_rating, review_count).
    """
    with transaction.atomic():
        if not lock_property(property_id):
            return Decimal("0.00"), 0  # property hi nahi bachi

        agg = Review.objects.filter(booking__property_id=property_id).aggregate(
            avg=Avg("rating"), cnt=Count("id")
        )
        count = agg["cnt"] or 0
        if count:
            average = Decimal(str(agg["avg"])).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            average = Decimal("0.00")

        Property.objects.filter(pk=property_id).update(
            average_rating=average, review_count=count
        )
        return average, count


def get_review_block_reason(booking, today):
    """Review likhne se rokne ki wajah (string) ya None."""
    if booking.status != STATUS_COMPLETED:
        return "You can review only completed stays."
    if today - booking.check_out > timedelta(days=REVIEW_WINDOW_DAYS):
        return (
            f"Review window closed. Reviews can be written within "
            f"{REVIEW_WINDOW_DAYS} days after check-out."
        )
    return None


def create_review(*, guest, booking_id, rating, comment, today=None):
    today = today or timezone.localdate()

    # Doosre guest ki booking ya nonexistent booking -> 404 (bookings app jaisa)
    try:
        booking = Booking.objects.select_related("property").get(
            pk=booking_id, guest=guest
        )
    except Booking.DoesNotExist:
        raise NotFound("Booking not found.")

    reason = get_review_block_reason(booking, today)
    if reason:
        raise ValidationError({"booking": [reason]})

    already_reviewed = False
    review = None
    with transaction.atomic():
        # Pehle property lock: ek booking ek hi property ki hoti hai, to
        # duplicate check lock ke BAAD race-free hai.
        lock_property(booking.property_id)

        if Review.objects.filter(booking_id=booking.pk).exists():
            already_reviewed = True
        else:
            review = Review.objects.create(
                booking=booking, rating=rating, comment=comment
            )
            recalculate_property_rating(booking.property_id)

    # Error atomic block ke BAAD raise (lesson 3)
    if already_reviewed:
        raise ReviewConflict()
    return review


def delete_review(review_id):
    """Admin moderation. Rating recompute post_delete signal se hota hai."""
    try:
        review = Review.objects.select_related("booking").get(pk=review_id)
    except Review.DoesNotExist:
        raise NotFound("Review not found.")

    property_id = review.booking.property_id
    with transaction.atomic():
        lock_property(property_id)
        review.delete()  # -> signal -> recalculate_property_rating

    prop = Property.objects.get(pk=property_id)
    return {
        "id": prop.pk,
        "average_rating": str(prop.average_rating),
        "review_count": prop.review_count,
    }