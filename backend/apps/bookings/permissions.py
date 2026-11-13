from rest_framework.permissions import BasePermission


class IsBookingParticipant(BasePermission):
    """Object-level: booking ka guest, property ka host, ya admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return bool(
            user.is_platform_admin
            or obj.guest_id == user.id
            or obj.property.host_id == user.id
        )


class IsBookingHostOrAdmin(BasePermission):
    """Object-level: sirf property ka host ya admin."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        return bool(user.is_platform_admin or obj.property.host_id == user.id)