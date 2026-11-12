from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Wishlist(TimeStampedModel):
    """Har user ki ek wishlist (signal se auto-create)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Wishlist of {self.user.username}"


class WishlistItem(TimeStampedModel):
    wishlist = models.ForeignKey(
        Wishlist,
        on_delete=models.CASCADE,
        related_name="items",
    )
    property = models.ForeignKey(
        "properties.Property",
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["wishlist", "property"],
                name="unique_wishlist_property",
            ),
        ]

    def __str__(self):
        return f"{self.property.title} in {self.wishlist}"