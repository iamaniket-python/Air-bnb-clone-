from decimal import Decimal

from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeBoundary, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Func, Q
from django.utils import timezone

from apps.core.models import TimeStampedModel

# In statuses mein booking dates "hold" rehti hain (overlap allowed nahi)
ACTIVE_BOOKING_STATUSES = ["pending", "confirmed"]


class DateRange(Func):
    """PostgreSQL DATERANGE(check_in, check_out, '[)') expression."""

    function = "DATERANGE"
    output_field = DateRangeField()


class Booking(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    guest = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    check_in = models.DateField()
    check_out = models.DateField()
    num_guests = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])

    # Price snapshot: booking ke time ka rate, baad mein property price badle to bhi safe
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["property", "check_in", "check_out"]),
            models.Index(fields=["guest", "status"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out__gt=F("check_in")),
                name="booking_checkout_after_checkin",
            ),
            models.CheckConstraint(
                condition=Q(num_guests__gte=1),
                name="booking_guests_gte_1",
            ),
            models.CheckConstraint(
                condition=Q(total_price__gte=0),
                name="booking_total_non_negative",
            ),
            # DB-level double booking protection:
            # same property + overlapping date range + active status = reject
            ExclusionConstraint(
                name="booking_no_overlap_per_property",
                expressions=[
                    (DateRange("check_in", "check_out", RangeBoundary()), RangeOperators.OVERLAPS),
                    ("property", RangeOperators.EQUAL),
                ],
                condition=Q(status__in=ACTIVE_BOOKING_STATUSES),
            ),
        ]

    def get_nights(self):
        return (self.check_out - self.check_in).days

    def clean(self):
        super().clean()
        errors = {}

        if self.check_in and self.check_out and self.check_out <= self.check_in:
            errors["check_out"] = "Check-out date check-in ke baad honi chahiye."

        if self._state.adding and self.check_in and self.check_in < timezone.localdate():
            errors["check_in"] = "Check-in date past mein nahi ho sakti."

        if self.property_id and self.num_guests and self.num_guests > self.property.max_guests:
            errors["num_guests"] = (
                f"Is property mein maximum {self.property.max_guests} guests allowed hain."
            )

        if self.guest_id and self.property_id and self.guest_id == self.property.host_id:
            errors["guest"] = "Host apni hi property book nahi kar sakta."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Booking #{self.pk} - {self.property.title} ({self.check_in} to {self.check_out})"