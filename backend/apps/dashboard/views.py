from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsHost, IsPlatformAdmin
from apps.properties.models import Property

from . import services
from .filters import AdminPropertyFilter, AdminUserFilter
from .serializers import (
    AdminPropertyActiveSerializer,
    AdminPropertySerializer,
    AdminUserActiveSerializer,
    AdminUserSerializer,
    UpcomingReservationSerializer,
)

User = get_user_model()


class HostDashboardView(APIView):
    """GET /api/host/dashboard/"""

    permission_classes = [IsHost]

    def get(self, request):
        data = services.get_host_dashboard(request.user)
        data["next_reservations"] = UpcomingReservationSerializer(
            data["next_reservations"], many=True
        ).data
        return Response(data)


class AdminDashboardView(APIView):
    """GET /api/admin/dashboard/"""

    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        return Response(services.get_admin_dashboard())


class AdminUserViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    GET   /api/admin/users/        filters: role, is_active, search, ordering
    GET   /api/admin/users/{id}/
    PATCH /api/admin/users/{id}/   {"is_active": bool}
    """

    permission_classes = [IsPlatformAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = StandardPagination
    filterset_class = AdminUserFilter
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["date_joined", "username", "last_login"]
    ordering = ["-date_joined", "-id"]
    http_method_names = ["get", "patch", "head", "options"]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        return User.objects.annotate(
            properties_count=Count("properties", distinct=True),
            bookings_count=Count("bookings", distinct=True),
        )

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = AdminUserActiveSerializer(
            user, data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        services.set_user_active(user, serializer.validated_data["is_active"])
        fresh = self.get_queryset().get(pk=user.pk)
        return Response(AdminUserSerializer(fresh).data)


class AdminPropertyViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    GET   /api/admin/properties/        inactive bhi; filters: is_active, property_type, city, host
    GET   /api/admin/properties/{id}/
    PATCH /api/admin/properties/{id}/   {"is_active": bool}
    """

    permission_classes = [IsPlatformAdmin]
    serializer_class = AdminPropertySerializer
    pagination_class = StandardPagination
    filterset_class = AdminPropertyFilter
    search_fields = ["title", "city", "host__username"]
    ordering_fields = ["created_at", "price_per_night", "average_rating", "review_count"]
    ordering = ["-created_at", "-id"]
    http_method_names = ["get", "patch", "head", "options"]
    lookup_value_regex = r"\d+"

    def get_queryset(self):
        return Property.objects.select_related("host").annotate(
            bookings_count=Count("bookings", distinct=True)
        )

    def partial_update(self, request, *args, **kwargs):
        prop = self.get_object()
        serializer = AdminPropertyActiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_property_active(prop, serializer.validated_data["is_active"])
        fresh = self.get_queryset().get(pk=prop.pk)
        return Response(AdminPropertySerializer(fresh).data)