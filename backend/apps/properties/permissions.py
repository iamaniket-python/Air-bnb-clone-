from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Read sab ke liye, write sirf platform admin ke liye (amenities)."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role == "admin")


class IsPropertyOwnerOrAdminOrReadOnly(BasePermission):
    """Object-level: read sab ke liye, write sirf property ka host ya admin."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user and user.is_authenticated and (user.role == "admin" or obj.host_id == user.id)
        )