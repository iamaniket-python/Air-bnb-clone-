from django.db import transaction

from .models import Wishlist, WishlistItem


def get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


def get_item_queryset(user):
    """User ki saari items (N+1 se bachne ke liye select/prefetch)."""
    return (
        WishlistItem.objects.filter(wishlist__user=user)
        .select_related("property", "property__host")
        .prefetch_related("property__images")
        .order_by("-created_at", "-id")
    )


def get_visible_items(user):
    """Sirf active properties wali items (inactive hide, row delete nahi)."""
    return get_item_queryset(user).filter(property__is_active=True)


def add_to_wishlist(user, property_obj):
    """Idempotent add. Returns (item, created). get_or_create race-safe hai."""
    wishlist = get_or_create_wishlist(user)
    with transaction.atomic():
        item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist, property=property_obj
        )
    return item, created


def remove_by_property(user, property_id):
    deleted, _ = WishlistItem.objects.filter(
        wishlist__user=user, property_id=property_id
    ).delete()
    return deleted > 0


def get_wishlisted_property_ids(user):
    return list(
        get_visible_items(user).values_list("property_id", flat=True)
    )