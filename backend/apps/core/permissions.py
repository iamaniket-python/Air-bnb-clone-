from rest_framework.permissions import SAFE_METHODS, BasePermission


class _RolePermission(BasePermission):
    """Base class: user ka role allowed_roles mein hona chahiye."""

    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in self.allowed_roles)


class IsGuest(_RolePermission):
    allowed_roles = ("guest",)


class IsHost(_RolePermission):
    allowed_roles = ("host",)


class IsPlatformAdmin(_RolePermission):
    allowed_roles = ("admin",)


class IsHostOrAdmin(_RolePermission):
    allowed_roles = ("host", "admin")


class IsHostOrReadOnly(BasePermission):
    """Read sab ke liye (logged-in ya anonymous), write sirf host/admin ke liye."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("host", "admin"))


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level: sirf owner ya admin.
    View par `owner_field` set karo (default "user"),
    e.g. Property ke liye owner_field = "host", Booking ke liye "guest".
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.role == "admin":
            return True
        owner_field = getattr(view, "owner_field", "user")
        return getattr(obj, owner_field) == user