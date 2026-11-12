from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """
    Custom user. Role se Guest / Host / Admin decide hota hai.
    Login abhi username se hai; Phase 3 mein email se login bhi support karenge.
    """

    class Role(models.TextChoices):
        GUEST = "guest", "Guest"
        HOST = "host", "Host"
        ADMIN = "admin", "Admin"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.GUEST,
        db_index=True,
    )
    phone_number = models.CharField(max_length=15, blank=True)

    def save(self, *args, **kwargs):
        # Superuser hamesha platform admin hoga
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_guest(self):
        return self.role == self.Role.GUEST

    @property
    def is_host(self):
        return self.role == self.Role.HOST

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return self.username


class UserProfile(TimeStampedModel):
    """Extra profile info. User banne par signal se auto-create hota hai."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    profile_picture = models.ImageField(upload_to="profiles/", blank=True)
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Profile of {self.user.username}"