import uuid
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class Payment(TimeStampedModel):
    """
    Ek booking ke liye multiple payment attempts ho sakte hain.
    Card details KABHI store nahi hoti, sirf gateway ke IDs aur status.
    """

    class Provider(models.TextChoices):
        MOCK = "mock", "Mock"
        RAZORPAY = "razorpay", "Razorpay"
        STRIPE = "stripe", "Stripe"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.PROTECT,
        related_name="payments",
    )
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    currency = models.CharField(max_length=3, default="INR")
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.MOCK,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Gateway references
    provider_order_id = models.CharField(max_length=100, blank=True)
    provider_payment_id = models.CharField(max_length=100, blank=True)
    provider_signature = models.CharField(max_length=255, blank=True)

    failure_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["provider_order_id"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive",
            ),
            # Same gateway payment ID dobara use nahi ho sakti (replay protection)
            models.UniqueConstraint(
                fields=["provider_payment_id"],
                condition=~Q(provider_payment_id=""),
                name="unique_provider_payment_id",
            ),
            # Ek booking par sirf ek successful payment
            models.UniqueConstraint(
                fields=["booking"],
                condition=Q(status="success"),
                name="one_successful_payment_per_booking",
            ),
        ]

    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"