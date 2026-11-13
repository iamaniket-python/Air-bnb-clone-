from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsGuest, IsPlatformAdmin
from apps.properties.models import Property

from . import services
from .serializers import ReviewCreateSerializer, ReviewSerializer


class ReviewListCreateView(generics.ListCreateAPIView):
    """
    POST /api/reviews/  -> guest review likhta hai
    GET  /api/reviews/  -> sirf admin (moderation list), filters: ?property=&rating=
    """

    serializer_class = ReviewSerializer
    pagination_class = StandardPagination
    filter_backends = []

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsGuest()]
        return [IsAuthenticated(), IsPlatformAdmin()]

    def get_queryset(self):
        qs = services.get_review_queryset()
        params = self.request.query_params
        property_id = params.get("property")
        rating = params.get("rating")
        if property_id and property_id.isdigit():
            qs = qs.filter(booking__property_id=int(property_id))
        if rating and rating.isdigit():
            qs = qs.filter(rating=int(rating))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        review = services.create_review(
            guest=request.user,
            booking_id=data["booking"],
            rating=data["rating"],
            comment=data["comment"],
        )
        review = services.get_review_queryset().get(pk=review.pk)
        return Response(ReviewSerializer(review).data, status=201)


class MyReviewListView(generics.ListAPIView):
    """GET /api/reviews/my/ -> guest ke apne reviews."""

    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsGuest]
    pagination_class = StandardPagination
    filter_backends = []

    def get_queryset(self):
        return services.get_review_queryset().filter(booking__guest=self.request.user)


class ReviewDeleteView(APIView):
    """DELETE /api/reviews/{id}/ -> sirf admin."""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def delete(self, request, pk):
        prop_data = services.delete_review(pk)
        return Response({"message": "Review deleted.", "property": prop_data})


class PropertyReviewListView(generics.ListAPIView):
    """GET /api/properties/{property_id}/reviews/ -> public, newest first."""

    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    filter_backends = []

    def _get_property(self):
        prop = Property.objects.filter(pk=self.kwargs["property_id"]).first()
        if prop is None:
            raise NotFound("Property not found.")
        user = self.request.user
        can_see_inactive = user.is_authenticated and (
            user.id == prop.host_id or user.is_platform_admin
        )
        if not prop.is_active and not can_see_inactive:
            raise NotFound("Property not found.")
        return prop

    def get_queryset(self):
        return services.get_review_queryset().filter(
            booking__property_id=self.property.pk
        )

    def list(self, request, *args, **kwargs):
        self.property = self._get_property()
        response = super().list(request, *args, **kwargs)
        response.data["summary"] = {
            "average_rating": str(self.property.average_rating),
            "review_count": self.property.review_count,
        }
        return response