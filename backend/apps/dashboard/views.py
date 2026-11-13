from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.core.pagination import StandardPagination
from apps.core.permissions import IsHost, IsPlatformAdmin
from apps.properties.models import Property

from . import services
from .serializers import (
    AdminPropertySerializer,
    AdminPropertyUpdateSerializer,
    AdminUserSerializer,
    AdminUserUpdateSerializer,
)


def parse_bool(value):
    if value is None:
        return None
    value = value.strip().lower()
    if value in ("true", "1"):
        return True
    if value in ("false", "0"):
        return False
    return None


# ------------------------------------------------------------------ host
class HostDashboardView(APIView):
    """GET /api/host/dashboard/"""

    permission_classes = [IsAuthenticated, IsHost]

    def get(self, request):
        return Response(services.get_host_dashboard(request.user))


# ----------------------------------------------------------------- admin
class AdminDashboardView(APIView):
    """GET /api/admin/dashboard/"""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request):
        return Response(services.get_admin_dashboard())


def admin_user_queryset():
    return User.objects.annotate(
        property_count=Count("properties", distinct=True),
        booking_count=Count("bookings", distinct=True),
    ).order_by("-date_joined", "-id")


class AdminUserListView(generics.ListAPIView):
    """GET /api/admin/users/?role=&is_active=&search="""

    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    pagination_class = StandardPagination
    filter_backends = []

    def get_queryset(self):
        qs = admin_user_queryset()
        params = self.request.query_params

        role = params.get("role")
        if role in services.ROLES:
            qs = qs.filter(role=role)

        is_active = parse_bool(params.get("is_active"))
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )
        return qs


class AdminUserDetailView(APIView):
    """GET/PATCH /api/admin/users/{id}/"""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def get(self, request, pk):
        user = get_object_or_404(admin_user_queryset(), pk=pk)
        return Response(AdminUserSerializer(user).data)

    def patch(self, request, pk):
        serializer = AdminUserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.update_user(
            request.user,
            pk,
            is_active=serializer.validated_data.get("is_active"),
            role=serializer.validated_data.get("role"),
        )
        user = admin_user_queryset().get(pk=pk)
        return Response({"message": "User updated.", "user": AdminUserSerializer(user).data})


def admin_property_queryset():
    return Property.objects.select_related("host").order_by("-created_at", "-id")


class AdminPropertyListView(generics.ListAPIView):
    """GET /api/admin/properties/?is_active=&host=&search="""

    serializer_class = AdminPropertySerializer
    permission_classes = [IsAuthenticated, IsPlatformAdmin]
    pagination_class = StandardPagination
    filter_backends = []

    def get_queryset(self):
        qs = admin_property_queryset()
        params = self.request.query_params

        is_active = parse_bool(params.get("is_active"))
        if is_active is not None:
            qs = qs.filter(is_active=is_active)

        host = params.get("host")
        if host and host.isdigit():
            qs = qs.filter(host_id=int(host))

        search = (params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(city__icontains=search))
        return qs


class AdminPropertyDetailView(APIView):
    """PATCH /api/admin/properties/{id}/  body {"is_active": true|false}"""

    permission_classes = [IsAuthenticated, IsPlatformAdmin]

    def patch(self, request, pk):
        serializer = AdminPropertyUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_property_active(pk, serializer.validated_data["is_active"])
        prop = admin_property_queryset().get(pk=pk)
        return Response(
            {"message": "Property updated.", "property": AdminPropertySerializer(prop).data}
        )