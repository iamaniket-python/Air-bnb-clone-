from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from apps.core.models import TimeStampedModel


class Amenity(TimeStampedModel):
    """Wi-Fi, AC, Pool, Parking, etc."""

    name = models.CharField(max_length=100, unique=True)
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="react-icons ka naam, e.g. FaWifi",
    )

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "amenities"

    def __str__(self):
        return self.name


class Property(TimeStampedModel):
    class PropertyType(models.TextChoices):
        APARTMENT = "apartment", "Apartment"
        HOUSE = "house", "House"
        VILLA = "villa", "Villa"
        COTTAGE = "cottage", "Cottage"
        GUEST_HOUSE = "guest_house", "Guest House"
        HOTEL = "hotel", "Hotel"
        RESORT = "resort", "Resort"

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="properties",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT,
    )

    # Location
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    postal_code = models.CharField(max_length=20, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Pricing and capacity
    price_per_night = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1.00"))],
    )
    max_guests = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    bedrooms = models.PositiveSmallIntegerField(default=1)
    beds = models.PositiveSmallIntegerField(default=1)
    bathrooms = models.PositiveSmallIntegerField(default=1)

    amenities = models.ManyToManyField(
        Amenity,
        through="PropertyAmenity",
        related_name="properties",
        blank=True,
    )

    # Soft delete / listing on-off
    is_active = models.BooleanField(default=True)

    # Denormalized rating data (Phase 8 mein reviews ke signals se update hoga)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "properties"
        indexes = [
            models.Index(fields=["city", "property_type"]),
            models.Index(fields=["price_per_night"]),
            models.Index(fields=["is_active", "-created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(price_per_night__gt=0),
                name="property_price_positive",
            ),
            models.CheckConstraint(
                condition=Q(max_guests__gte=1),
                name="property_max_guests_gte_1",
            ),
            models.CheckConstraint(
                condition=Q(average_rating__gte=0) & Q(average_rating__lte=5),
                name="property_avg_rating_0_to_5",
            ),
        ]

    def clean(self):
        super().clean()
        if self.host_id and not self.host.is_host:
            raise ValidationError(
                {"host": "Sirf 'host' role wale users property own kar sakte hain."}
            )

    def __str__(self):
        return f"{self.title} ({self.city})"


class PropertyImage(TimeStampedModel):
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="properties/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["-is_primary", "display_order", "id"]
        constraints = [
            # Ek property ki sirf ek primary image
            models.UniqueConstraint(
                fields=["property"],
                condition=Q(is_primary=True),
                name="one_primary_image_per_property",
            ),
        ]

    def __str__(self):
        return f"Image {self.pk} of {self.property.title}"


class PropertyAmenity(TimeStampedModel):
    """Property aur Amenity ke beech explicit through table."""

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name="property_amenities",
    )
    amenity = models.ForeignKey(
        Amenity,
        on_delete=models.CASCADE,
        related_name="property_amenities",
    )

    class Meta:
        verbose_name_plural = "property amenities"
        constraints = [
            models.UniqueConstraint(
                fields=["property", "amenity"],
                name="unique_property_amenity",
            ),
        ]

    def __str__(self):
        return f"{self.property.title} - {self.amenity.name}"