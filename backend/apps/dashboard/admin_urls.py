from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import AdminDashboardView, AdminPropertyViewSet, AdminUserViewSet

app_name = "platform_admin"

router = SimpleRouter()
router.register(r"users", AdminUserViewSet, basename="admin-user")
router.register(r"properties", AdminPropertyViewSet, basename="admin-property")

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]