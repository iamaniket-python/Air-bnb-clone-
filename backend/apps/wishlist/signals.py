from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Wishlist


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_wishlist(sender, instance, created, **kwargs):
    """Naya user bante hi uski wishlist ban jaye."""
    if created:
        Wishlist.objects.create(user=instance)