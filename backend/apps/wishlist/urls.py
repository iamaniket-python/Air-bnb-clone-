from django.urls import path

from .views import (
    WishlistIdsView,
    WishlistItemDeleteView,
    WishlistListCreateView,
    WishlistRemoveByPropertyView,
)

app_name = "wishlist"

urlpatterns = [
    path("", WishlistListCreateView.as_view(), name="wishlist-list-create"),
    path("ids/", WishlistIdsView.as_view(), name="wishlist-ids"),
    path(
        "property/<int:property_id>/",
        WishlistRemoveByPropertyView.as_view(),
        name="wishlist-remove-by-property",
    ),
    path("<int:pk>/", WishlistItemDeleteView.as_view(), name="wishlist-item-delete"),
]