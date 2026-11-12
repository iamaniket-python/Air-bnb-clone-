from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsHost, IsHostOrAdmin

from .filters import PropertyFilter, StableOrderingFilter
from .models import Amenity, Property, PropertyImage
from .permissions import IsAdminOrReadOnly, IsPropertyOwnerOrAdminOrReadOnly
from .serializers import (
    AmenitySerializer,
    PropertyDetailSerializer,
    PropertyImageSerializer,
    PropertyImageUpdateSerializer,
    PropertyImageUploadSerializer,
    PropertyListSerializer,
    PropertyWriteSerializer,
)
from .services import (
    add_property_images,
    delete_property,
    delete_property_image,
    update_property_image,
)


class AmenityViewSet(viewsets.ModelViewSet):
    """Read: public. Create/update/delete: sirf admin."""

    queryset = Amenity.objects.all()
    serializer_class = AmenitySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None  # amenities kam hain, poori list ek saath


class PropertyViewSet(viewsets.ModelViewSet):
    """
    list / retrieve : public (list mein sirf active properties, search + filters ke saath)
    create          : sirf host
    update / delete : owner host ya admin
    my              : host ki apni saari listings (filters yahan bhi chalte hain)
    destinations    : search bar autocomplete
    images          : image upload / update / delete
    """

    # Search, filter, sort, pagination (sirf list par; filter_queryset niche dekho)
    filter_backends = [DjangoFilterBackend, SearchFilter, StableOrderingFilter]
    filterset_class = PropertyFilter
    search_fields = ["title", "city", "state", "address"]
    ordering_fields = ["price_per_night", "average_rating", "review_count", "created_at"]
    ordering = ["-created_at", "-id"]
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve", "destinations"):
            permission_classes = [AllowAny]
        elif self.action in ("create", "my"):
            permission_classes = [IsHost]
        else:  # update, partial_update, destroy, upload_images, manage_image
            permission_classes = [IsHostOrAdmin, IsPropertyOwnerOrAdminOrReadOnly]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action in ("list", "my"):
            return PropertyListSerializer
        if self.action == "retrieve":
            return PropertyDetailSerializer
        return PropertyWriteSerializer

    def get_queryset(self):
        user = self.request.user

        if self.action in ("list", "my"):
            # Card ko sirf 1 image chahiye: sliced Prefetch se har property ki sirf pehli
            # (primary) image aati hai. Profile/amenities bhi nahi chahiye.
            queryset = Property.objects.select_related("host").prefetch_related(
                Prefetch("images", queryset=PropertyImage.objects.all()[:1])
            )
        else:
            queryset = Property.objects.select_related("host__profile").prefetch_related(
                "images", "amenities"
            )

        if self.action == "list":
            return queryset.filter(is_active=True)
        if self.action == "my":
            return queryset.filter(host=user)
        if user.is_authenticated and user.role == "admin":
            return queryset
        if user.is_authenticated:
            # Active properties + user ki apni (inactive bhi)
            return queryset.filter(Q(is_active=True) | Q(host=user))
        return queryset.filter(is_active=True)

    def filter_queryset(self, queryset):
        # DRF ka get_object() bhi filter_queryset chalata hai. Filters sirf listing par
        # lagne chahiye, warna /properties/1/?min_price=99999 detail ko 404 bana deta.
        if self.action in ("list", "my"):
            return super().filter_queryset(queryset)
        return queryset

    def perform_create(self, serializer):
        serializer.save(host=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        deleted_permanently = delete_property(instance)
        message = (
            "Property deleted permanently."
            if deleted_permanently
            else "Property has booking history, so it was deactivated instead of deleted."
        )
        return Response({"message": message})

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """GET /api/properties/my/"""
        return self.list(request)

    @action(detail=False, methods=["get"], url_path="destinations")
    def destinations(self, request):
        """GET /api/properties/destinations/?q=go  (search bar suggestions, max 8)"""
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response([])

        rows = (
            Property.objects.filter(is_active=True)
            .filter(Q(city__icontains=query) | Q(state__icontains=query))
            .values("city", "state", "country")
            .annotate(property_count=Count("id"))
            .order_by("-property_count", "city")[:8]
        )
        return Response(list(rows))

    @action(
        detail=True,
        methods=["post"],
        url_path="images",
        parser_classes=[MultiPartParser, FormParser],
    )
    def upload_images(self, request, pk=None):
        """POST /api/properties/{id}/images/  (multipart, key: images, multiple files)"""
        prop = self.get_object()
        serializer = PropertyImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        images = add_property_images(prop, serializer.validated_data["images"])
        return Response(
            PropertyImageSerializer(images, many=True, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["patch", "delete"],
        url_path=r"images/(?P<image_id>[0-9]+)",
    )
    def manage_image(self, request, pk=None, image_id=None):
        """PATCH / DELETE /api/properties/{id}/images/{image_id}/"""
        prop = self.get_object()
        image = get_object_or_404(PropertyImage, pk=image_id, property=prop)

        if request.method == "DELETE":
            delete_property_image(image)
            return Response({"message": "Image deleted."})

        serializer = PropertyImageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image = update_property_image(image, serializer.validated_data)
        return Response(PropertyImageSerializer(image, context={"request": request}).data)