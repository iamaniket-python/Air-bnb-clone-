from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsGuest

from . import services
from .serializers import WishlistAddSerializer, WishlistItemSerializer


class WishlistListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/wishlist/  -> meri wishlist (property cards, paginated)
    POST /api/wishlist/  -> {"property": id}  (idempotent: 201 naya, 200 pehle se tha)
    """

    serializer_class = WishlistItemSerializer
    permission_classes = [IsAuthenticated, IsGuest]
    pagination_class = StandardPagination
    filter_backends = []

    def get_queryset(self):
        return services.get_visible_items(self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = WishlistAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item, created = services.add_to_wishlist(
            request.user, serializer.validated_data["property"]
        )
        item = services.get_item_queryset(request.user).get(pk=item.pk)
        data = WishlistItemSerializer(item, context={"request": request}).data

        message = "Added to wishlist." if created else "Property is already in your wishlist."
        return Response(
            {"message": message, "created": created, "item": data},
            status=201 if created else 200,
        )


class WishlistItemDeleteView(generics.DestroyAPIView):
    """DELETE /api/wishlist/{id}/  ({id} = WishlistItem id). Doosre ki item par 404."""

    permission_classes = [IsAuthenticated, IsGuest]

    def get_queryset(self):
        return services.get_item_queryset(self.request.user)


class WishlistRemoveByPropertyView(APIView):
    """DELETE /api/wishlist/property/{property_id}/  (heart toggle ke liye)."""

    permission_classes = [IsAuthenticated, IsGuest]

    def delete(self, request, property_id):
        if not services.remove_by_property(request.user, property_id):
            raise NotFound("Property is not in your wishlist.")
        return Response(status=204)


class WishlistIdsView(APIView):
    """GET /api/wishlist/ids/ -> {"property_ids": [...]} (heart state ke liye)."""

    permission_classes = [IsAuthenticated, IsGuest]

    def get(self, request):
        return Response({"property_ids": services.get_wishlisted_property_ids(request.user)})