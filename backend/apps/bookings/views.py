from rest_framework import mixins, viewsets
from rest_framework import status as http_status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsGuest, IsHostOrAdmin

from . import services
from .filters import BookingFilter
from .models import Booking
from .permissions import IsBookingHostOrAdmin, IsBookingParticipant
from .serializers import (
    BookingCancelSerializer,
    BookingCreateSerializer,
    BookingQuoteSerializer,
    BookingSerializer,
    BookingStatusSerializer,
)


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BookingSerializer
    pagination_class = StandardPagination
    filterset_class = BookingFilter
    search_fields = ["property__title", "property__city", "guest__username"]
    ordering_fields = ["check_in", "check_out", "created_at", "total_price"]
    ordering = ["-created_at", "-id"]
    lookup_value_regex = r"\d+"

    # ---- permissions -------------------------------------------------------
    def get_permissions(self):
        if self.action == "quote":
            return [AllowAny()]
        if self.action == "create":
            return [IsAuthenticated(), IsGuest()]
        if self.action == "change_status":
            return [IsAuthenticated(), IsHostOrAdmin(), IsBookingHostOrAdmin()]
        # list, retrieve, cancel
        return [IsAuthenticated(), IsBookingParticipant()]

    # ---- role-based visibility ----------------------------------------------
    def get_queryset(self):
        qs = Booking.objects.select_related(
            "property", "property__host", "guest"
        ).prefetch_related("property__images")

        user = self.request.user
        if user.is_platform_admin:
            return qs
        if user.is_host:
            return qs.filter(property__host=user)
        return qs.filter(guest=user)

    def _respond(self, booking_id, http_status_code=http_status.HTTP_200_OK, extra=None):
        booking = self.get_queryset().get(pk=booking_id)
        data = BookingSerializer(booking, context=self.get_serializer_context()).data
        if extra:
            data = {**extra, "booking": data}
        return Response(data, status=http_status_code)

    # ---- endpoints -----------------------------------------------------------
    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = services.create_booking(
            guest=request.user,
            property_id=data["property"].pk,
            check_in=data["check_in"],
            check_out=data["check_out"],
            num_guests=data["num_guests"],
        )
        return self._respond(booking.pk, http_status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="quote", url_name="quote")
    def quote(self, request):
        serializer = BookingQuoteSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = services.quote_stay(
            property_obj=data["property"],
            user=request.user,
            check_in=data["check_in"],
            check_out=data["check_out"],
            num_guests=data["guests"],
        )
        return Response(result)

    @action(detail=True, methods=["patch"], url_path="status", url_name="status")
    def change_status(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        services.change_status(
            booking_id=booking.pk,
            actor=request.user,
            new_status=serializer.validated_data["status"],
            reason=serializer.validated_data.get("reason", ""),
        )
        return self._respond(booking.pk)

    @action(detail=True, methods=["post"], url_path="cancel", url_name="cancel")
    def cancel(self, request, pk=None):
        booking = self.get_object()
        serializer = BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        _, refund_percentage = services.cancel_booking(
            booking_id=booking.pk,
            actor=request.user,
            reason=serializer.validated_data.get("reason", ""),
        )
        return self._respond(
            booking.pk,
            extra={
                "message": "Booking cancelled successfully.",
                "refund_percentage": refund_percentage,
            },
        )