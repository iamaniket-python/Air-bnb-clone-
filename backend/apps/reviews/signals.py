from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.bookings.models import Booking

from .models import Review
from .services import recalculate_property_rating


@receiver(post_delete, sender=Review)
def refresh_rating_after_review_delete(sender, instance, **kwargs):
    """
    Review kisi bhi tareeke se delete ho (API, Django admin, shell),
    property ki denormalized rating hamesha sahi rehni chahiye.
    """
    property_id = (
        Booking.objects.filter(pk=instance.booking_id)
        .values_list("property_id", flat=True)
        .first()
    )
    if property_id:
        recalculate_property_rating(property_id)