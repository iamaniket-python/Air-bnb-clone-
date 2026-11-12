"""
Properties ka business logic: images aur delete rules.
"""
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bookings.models import ACTIVE_BOOKING_STATUSES

from .models import Property, PropertyImage

MAX_IMAGES_PER_PROPERTY = 15


def add_property_images(prop, files):
    """
    Multiple images upload. Pehli image apne aap primary banti hai
    (agar property mein abhi koi primary nahi hai).
    Property row lock hoti hai taaki concurrent uploads mein 2 primary na ban jayein.
    """
    with transaction.atomic():
        locked = Property.objects.select_for_update().get(pk=prop.pk)

        existing = locked.images.count()
        if existing + len(files) > MAX_IMAGES_PER_PROPERTY:
            raise ValidationError(
                {
                    "images": (
                        f"A property can have at most {MAX_IMAGES_PER_PROPERTY} images "
                        f"(currently {existing})."
                    )
                }
            )

        has_primary = locked.images.filter(is_primary=True).exists()
        last_order = locked.images.aggregate(last=Max("display_order"))["last"]
        next_order = 0 if last_order is None else last_order + 1

        created = []
        for index, file in enumerate(files):
            created.append(
                PropertyImage.objects.create(
                    property=locked,
                    image=file,
                    display_order=next_order + index,
                    is_primary=(not has_primary and index == 0),
                )
            )
        return created


def set_primary_image(image):
    """Pehle purani primary hatao, phir nayi set karo (unique constraint ke liye order zaroori)."""
    with transaction.atomic():
        PropertyImage.objects.filter(
            property_id=image.property_id, is_primary=True
        ).exclude(pk=image.pk).update(is_primary=False)

        if not image.is_primary:
            image.is_primary = True
            image.save(update_fields=["is_primary", "updated_at"])
    return image


def update_property_image(image, data):
    with transaction.atomic():
        wants_primary = data.get("is_primary")

        if wants_primary is False and image.is_primary:
            raise ValidationError(
                {"is_primary": "Set another image as primary instead of unsetting this one."}
            )

        for field in ("caption", "display_order"):
            if field in data:
                setattr(image, field, data[field])
        image.save()

        if wants_primary:
            set_primary_image(image)
    return image


def delete_property_image(image):
    """File storage se bhi hatao. Primary delete ho to agli image primary ban jaye."""
    with transaction.atomic():
        was_primary = image.is_primary
        property_id = image.property_id

        image.image.delete(save=False)
        image.delete()

        if was_primary:
            next_image = PropertyImage.objects.filter(property_id=property_id).first()
            if next_image:
                next_image.is_primary = True
                next_image.save(update_fields=["is_primary", "updated_at"])


def delete_property(prop):
    """
    Delete rules:
    - upcoming pending/confirmed booking hai -> block
    - kabhi koi booking nahi hui -> permanent delete (images bhi)
    - purani bookings hain -> soft delete (history safe rahe)
    Return: True agar permanently delete hui, False agar soft delete.
    """
    today = timezone.localdate()

    if prop.bookings.filter(status__in=ACTIVE_BOOKING_STATUSES, check_out__gt=today).exists():
        raise ValidationError(
            {
                "detail": (
                    "This property has upcoming pending/confirmed bookings. "
                    "Cancel or complete them before deleting."
                )
            }
        )

    with transaction.atomic():
        if prop.bookings.exists():
            prop.is_active = False
            prop.save(update_fields=["is_active", "updated_at"])
            return False

        for image in prop.images.all():
            image.image.delete(save=False)
        prop.delete()
        return True