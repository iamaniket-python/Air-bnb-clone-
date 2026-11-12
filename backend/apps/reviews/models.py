from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

from apps.bookings.models import Booking
from apps.core.models import TimeStampedModel


class Review(TimeStampedModel):
    """
    Review booking se linked hai (One-to-One), isliye:
    - ek booking par duplicate review DB level par impossible
    - property aur guest booking se mil jaate hain (no redundancy)
    """

    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name="review",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1) & Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
        ]

    def clean(self):
        super().clean()
        if self.booking_id and self.booking.status != Booking.Status.COMPLETED:
            raise ValidationError(
                {"booking": "Sirf completed bookings par review diya ja sakta hai."}
            )

    def __str__(self):
        return f"Review {self.rating}/5 for booking #{self.booking_id}"